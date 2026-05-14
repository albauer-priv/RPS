---
Version: 1.0
Status: Updated
Last-Updated: 2026-05-14
Owner: Runbooks
---
# CrewAI Static Knowledge

## Purpose

Describe which static references now map into CrewAI knowledge sources.

## Config

See `config/crewai/knowledge_sources.yaml`.

Knowledge bundles include examples such as:
- `durability_core`
- `coach_static`
- `season_static`
- `phase_static`
- `week_static`
- `report_static`

## Boundary

CrewAI Knowledge is for static domain/reference material only.

Do not use it for:
- live athlete runtime facts
- selected latest artifact payloads
- pending operation payloads
- schema-bound authoritative truth

## Runtime notes

RPS currently materializes configured files as CrewAI string knowledge sources when CrewAI is available.
