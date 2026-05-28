"""Primary-source discovery plus staged curation/activation for evidence entries."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import UTC, date, datetime, timedelta
from hashlib import sha1
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from .library import (
    CURATION_SCHEMA_VERSION,
    DISCOVERY_LOCK_PATH,
    EvidenceEntry,
    get_discovery_state,
    load_applied_sources,
    load_core_studies,
    save_applied_sources,
    save_core_studies,
    save_discovery_state,
    sync_reference_library_outputs,
)
from .pipeline import run_entry_pipeline

logger = logging.getLogger(__name__)

_PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
_PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
_DEFAULT_QUERY_RETMAX = 10
_DEFAULT_REFRESH_INTERVAL_DAYS = 7
_DEFAULT_LEGACY_BACKFILL_LIMIT = 1
_DEFAULT_MAX_ENTRIES_PER_REFRESH = 5
_DEFAULT_ABSTRACT_FETCH_RETRIES = 2
DISCOVERY_TOPICS: tuple[tuple[str, str], ...] = (
    ("durability", "\"durability\" AND cycling"),
    ("fatigue_resistance", "\"fatigue resistance\" AND cycling"),
    ("repeatability", "\"repeatability\" AND endurance"),
    ("progressive_overload", "\"endurance training\" AND periodization AND cycling"),
    ("taper", "taper AND endurance athletes"),
    ("fueling", "carbohydrate fueling endurance cycling"),
    ("masters", "masters endurance cycling training"),
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _json_get(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=20) as response:  # nosec B310 - controlled primary-source URLs
        return json.loads(response.read().decode("utf-8"))


def _text_get(url: str) -> str:
    with urlopen(url, timeout=20) as response:  # nosec B310 - controlled primary-source URLs
        return response.read().decode("utf-8")


def _search_pubmed(query: str, *, start_date: date, end_date: date, retmax: int = _DEFAULT_QUERY_RETMAX) -> list[str]:
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": str(retmax),
        "datetype": "pdat",
        "mindate": start_date.isoformat(),
        "maxdate": end_date.isoformat(),
    }
    payload = _json_get(f"{_PUBMED_SEARCH_URL}?{urlencode(params)}")
    return [str(item) for item in (((payload.get("esearchresult") or {}).get("idlist")) or [])]


def _summaries_pubmed(ids: list[str]) -> list[dict[str, Any]]:
    if not ids:
        return []
    params = {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
    payload = _json_get(f"{_PUBMED_SUMMARY_URL}?{urlencode(params)}")
    result = payload.get("result") or {}
    summaries: list[dict[str, Any]] = []
    for pmid in ids:
        item = result.get(str(pmid))
        if isinstance(item, dict):
            summaries.append(item)
    return summaries


def _fetch_pubmed_abstract(pmid: str) -> str:
    params = {"db": "pubmed", "id": pmid, "retmode": "text", "rettype": "abstract"}
    text = _text_get(f"{_PUBMED_FETCH_URL}?{urlencode(params)}")
    cleaned = text.strip()
    return cleaned if len(cleaned) > 40 else ""


def _doi_from_locator(locator: str) -> str | None:
    match = re.search(r"doi\.org/(.+)$", locator.strip(), flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip() or None


def _resolve_pubmed_id_from_doi(doi: str) -> str | None:
    """Resolve one DOI to a PubMed identifier when PubMed has the paper indexed."""

    normalized = doi.strip()
    if not normalized:
        return None
    query_variants = (
        f'"{normalized}"[AID]',
        f'"{normalized}"[doi]',
        normalized,
    )
    for query in query_variants:
        try:
            ids = _search_pubmed(query, start_date=date(1900, 1, 1), end_date=_utc_now().date(), retmax=1)
        except Exception as exc:  # pragma: no cover - network/runtime guard
            logger.warning("Evidence DOI->PubMed resolution failed for doi=%s query=%s: %s", normalized, query, exc)
            return None
        if ids:
            return ids[0]
    logger.warning("Evidence DOI->PubMed resolution returned no match for doi=%s", normalized)
    return None


def _fetch_pubmed_abstract_with_backoff(
    pmid: str,
    *,
    retries: int = _DEFAULT_ABSTRACT_FETCH_RETRIES,
    base_sleep_seconds: float = 1.0,
) -> tuple[str, bool]:
    """Return abstract text plus a flag indicating rate-limit exhaustion."""

    attempt = 0
    while True:
        try:
            return _fetch_pubmed_abstract(pmid), False
        except HTTPError as exc:
            if exc.code != 429 or attempt >= retries:
                if exc.code == 429:
                    return "", True
                raise
            sleep_seconds = base_sleep_seconds * (2**attempt)
            logger.warning("Evidence abstract fetch rate-limited for pmid=%s; retrying in %.1fs", pmid, sleep_seconds)
            time.sleep(sleep_seconds)
            attempt += 1


def _normalized_title(value: str) -> str:
    return " ".join(value.lower().replace("’", "'").replace("“", '"').replace("”", '"').split())


def _existing_title_index(entries: list[EvidenceEntry]) -> set[str]:
    return {_normalized_title(entry.title) for entry in entries}


def _summary_to_entry(summary: dict[str, Any], *, topic_tag: str, discovered_at: str) -> EvidenceEntry | None:
    title = str(summary.get("title") or "").strip().rstrip(".")
    if not title:
        return None
    authors_list = summary.get("authors") or []
    authors = ", ".join(
        str(item.get("name") or "").strip()
        for item in authors_list
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    )
    pubdate = str(summary.get("pubdate") or "")
    year = 0
    for token in pubdate.split():
        if token[:4].isdigit():
            year = int(token[:4])
            break
    if not authors or year <= 0:
        return None
    article_ids = summary.get("articleids") or []
    doi = None
    for item in article_ids:
        if isinstance(item, dict) and str(item.get("idtype") or "").lower() == "doi":
            doi = str(item.get("value") or "").strip()
            break
    pmid = str(summary.get("uid") or "").strip()
    if doi:
        locator = f"https://doi.org/{doi}"
        locator_source = "doi"
        verification_status = "verified"
    elif pmid:
        locator = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        locator_source = "pubmed"
        verification_status = "verified"
    else:
        return None
    journal = str(summary.get("fulljournalname") or summary.get("source") or "").strip()
    stable_suffix = sha1(f"{title}|{authors}|{year}".encode("utf-8")).hexdigest()[:10]
    safe_id = f"dur_auto_{year}_{stable_suffix}"
    return EvidenceEntry.from_mapping(
        {
            "id": safe_id,
            "source_kind": "core",
            "authors": authors,
            "year": year,
            "title": title,
            "journal_or_outlet": journal,
            "source_type": "peer_reviewed",
            "study_type": "other",
            "reference_locator": locator,
            "verification_status": verification_status,
            "locator_source": locator_source,
            "topic_tags": [topic_tag, "cycling_endurance"],
            "question_or_focus": "Auto-discovered primary-source candidate pending structured curation.",
            "population_or_scope": "Primary-source discovery candidate.",
            "authority_limit": "background_only",
            "evidence_posture": "metadata_only_not_activatable",
            "fulltext_status": "link_only",
            "source_material_level": "metadata_only",
            "source_material_basis": "Metadata-only package; not activatable without stronger source text.",
            "notes": "Added by automatic weekly primary-source discovery.",
            "brief_status": "pending_curation",
            "activation_status": "verified",
            "trusted_source_match": False,
            "trusted_match_reason": "",
            "legacy_active": False,
            "curation_schema_version": "1",
            "last_verified_at": discovered_at,
            "discovered_at": discovered_at,
            "record_fingerprint": safe_id,
        },
        source_kind="core",
    )


def _pmid_from_locator(locator: str) -> str | None:
    match = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/", locator)
    return match.group(1) if match else None


def _resolve_pubmed_id_for_entry(entry: EvidenceEntry) -> str | None:
    """Return a PubMed ID for one entry when resolvable from its stored locator."""

    direct_pmid = _pmid_from_locator(entry.reference_locator)
    if direct_pmid:
        return direct_pmid
    doi = _doi_from_locator(entry.reference_locator)
    if not doi:
        return None
    return _resolve_pubmed_id_from_doi(doi)


def evidence_refresh_due(*, now: datetime | None = None, interval_days: int = _DEFAULT_REFRESH_INTERVAL_DAYS) -> bool:
    """Return True when the evidence refresh is due."""

    state = get_discovery_state()
    last_success = state.get("last_success_at")
    if not isinstance(last_success, str) or not last_success.strip():
        return True
    try:
        last_dt = datetime.fromisoformat(last_success.replace("Z", "+00:00"))
    except ValueError:
        return True
    return (now or _utc_now()) >= last_dt + timedelta(days=interval_days)


def _entry_requires_processing(entry: EvidenceEntry) -> bool:
    """Return whether one entry should enter the curation pipeline in this run."""

    if entry.activation_status == "candidate":
        return True
    if (
        entry.legacy_active
        and entry.verification_status == "verified"
        and not entry.curated_at
        and entry.brief_status == "pending_curation"
    ):
        return True
    if entry.activation_status == "verified":
        if not entry.curated_at:
            return True
        if entry.curation_schema_version != CURATION_SCHEMA_VERSION:
            return True
        if entry.brief_status in {"", "pending_curation"}:
            return True
    return False


def _curate_candidates(
    entries: list[EvidenceEntry],
    *,
    athlete_id: str,
    run_id: str,
    workspace_root,
    stats: dict[str, int],
    legacy_backfill_limit: int,
    max_entries_per_refresh: int,
) -> list[EvidenceEntry]:
    refreshed: list[EvidenceEntry] = []
    legacy_backfilled = 0
    processed_entries = 0
    for entry in entries:
        should_process_by_state = _entry_requires_processing(entry)
        abstract_text = ""
        pmid = _resolve_pubmed_id_for_entry(entry) if should_process_by_state or entry.legacy_active else None
        rate_limited = False
        if pmid and should_process_by_state:
            try:
                abstract_text, rate_limited = _fetch_pubmed_abstract_with_backoff(pmid)
            except Exception as exc:  # pragma: no cover - network/runtime guard
                logger.warning("Evidence abstract fetch failed for %s: %s", entry.id, exc)
        should_backfill_legacy = entry.legacy_active and legacy_backfilled < legacy_backfill_limit and bool(abstract_text)
        should_process = should_process_by_state or should_backfill_legacy
        if not should_process:
            stats["skipped_unchanged"] += 1
            refreshed.append(entry)
            continue
        if processed_entries >= max_entries_per_refresh:
            stats["skipped_due_to_cap"] += 1
            refreshed.append(entry)
            continue
        if rate_limited and should_process_by_state and not abstract_text:
            stats["rate_limited_skipped"] += 1
            refreshed.append(entry)
            continue
        result_entry, result = run_entry_pipeline(
            entry,
            athlete_id=athlete_id,
            run_id=run_id,
            workspace_root=workspace_root,
            abstract_text=abstract_text,
        )
        processed_entries += 1
        stats["processed_entries"] += 1
        if should_backfill_legacy:
            legacy_backfilled += 1
            stats["legacy_backfilled"] += 1
        status = str(result.get("status") or "")
        if status == "active":
            stats["activated_entries"] += 1
        elif status == "curated":
            stats["curated_hold_entries"] += 1
        elif status == "rejected":
            stats["rejected_entries"] += 1
        elif status == "legacy_retained":
            stats["quality_gate_failed"] += 1
        refreshed.append(result_entry)
    return refreshed


def refresh_evidence_library(
    *,
    now: datetime | None = None,
    refresh_interval_days: int = _DEFAULT_REFRESH_INTERVAL_DAYS,
    retmax: int = _DEFAULT_QUERY_RETMAX,
    athlete_id: str = "system",
    workspace_root=None,
    run_id: str = "",
    legacy_backfill_limit: int = _DEFAULT_LEGACY_BACKFILL_LIMIT,
    max_entries_per_refresh: int = _DEFAULT_MAX_ENTRIES_PER_REFRESH,
) -> dict[str, Any]:
    """Refresh the canonical evidence library from primary-source discovery and curation."""

    current_now = now or _utc_now()
    if not evidence_refresh_due(now=current_now, interval_days=refresh_interval_days):
        return {"status": "skipped", "reason": "not_due", "at": current_now.isoformat()}
    DISCOVERY_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock_fd = os.open(DISCOVERY_LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return {"status": "skipped", "reason": "locked", "at": current_now.isoformat()}

    try:
        with os.fdopen(lock_fd, "w", encoding="utf-8") as handle:
            handle.write(current_now.isoformat().replace("+00:00", "Z"))

        state = get_discovery_state()
        state["last_attempt_at"] = current_now.isoformat().replace("+00:00", "Z")

        last_search_date_raw = state.get("last_search_date")
        if isinstance(last_search_date_raw, str) and last_search_date_raw:
            try:
                start_date = date.fromisoformat(last_search_date_raw) + timedelta(days=1)
            except ValueError:
                start_date = (current_now - timedelta(days=refresh_interval_days)).date()
        else:
            start_date = (current_now - timedelta(days=refresh_interval_days)).date()
        end_date = current_now.date()

        core_entries = load_core_studies()
        applied_entries = load_applied_sources()
        existing_titles = _existing_title_index(core_entries)
        stats = {
            "queries_run": 0,
            "candidates_seen": 0,
            "new_candidates_added": 0,
            "duplicates_skipped": 0,
            "unresolved_skipped": 0,
            "activated_entries": 0,
            "curated_hold_entries": 0,
            "rejected_entries": 0,
            "quality_gate_failed": 0,
            "legacy_backfilled": 0,
            "processed_entries": 0,
            "skipped_unchanged": 0,
            "skipped_due_to_cap": 0,
            "rate_limited_skipped": 0,
        }
        discovered_at = current_now.date().isoformat()

        for topic_tag, query in DISCOVERY_TOPICS:
            stats["queries_run"] += 1
            try:
                ids = _search_pubmed(query, start_date=start_date, end_date=end_date, retmax=retmax)
                summaries = _summaries_pubmed(ids)
            except Exception as exc:  # pragma: no cover - network/runtime guard
                logger.warning("Evidence discovery query failed for %s: %s", topic_tag, exc)
                continue
            for summary in summaries:
                stats["candidates_seen"] += 1
                candidate = _summary_to_entry(summary, topic_tag=topic_tag, discovered_at=discovered_at)
                if candidate is None or candidate.verification_status != "verified":
                    stats["unresolved_skipped"] += 1
                    continue
                title_key = _normalized_title(candidate.title)
                if title_key in existing_titles:
                    stats["duplicates_skipped"] += 1
                    continue
                existing_titles.add(title_key)
                core_entries.append(candidate)
                stats["new_candidates_added"] += 1

        core_entries.sort(key=lambda item: (item.year, item.title.lower()))
        original_core_entries = core_entries.copy()
        original_applied_entries = applied_entries.copy()
        core_entries = _curate_candidates(
            core_entries,
            athlete_id=athlete_id,
            run_id=run_id,
            workspace_root=workspace_root,
            stats=stats,
            legacy_backfill_limit=legacy_backfill_limit,
            max_entries_per_refresh=max_entries_per_refresh,
        )

        library_changed = core_entries != original_core_entries or applied_entries != original_applied_entries
        if library_changed:
            save_core_studies(core_entries)
            save_applied_sources(applied_entries)
            sync_reference_library_outputs(rewrite_yaml=False)

        state["last_success_at"] = current_now.isoformat().replace("+00:00", "Z")
        state["last_search_date"] = end_date.isoformat()
        state["stats"] = stats
        save_discovery_state(state)
        return {
            "status": "done",
            "at": current_now.isoformat(),
            "stats": stats,
            "library_changed": library_changed,
        }
    finally:
        try:
            DISCOVERY_LOCK_PATH.unlink(missing_ok=True)
        except OSError:  # pragma: no cover - best effort cleanup
            logger.warning("Unable to remove evidence refresh lock %s", DISCOVERY_LOCK_PATH)
