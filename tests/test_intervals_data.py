from __future__ import annotations

import math

from rps.data_pipeline.intervals_data import _power_zone_share_percent


def test_power_zone_share_percent_uses_pure_z2_when_requested():
    zone_seconds = {1: 2400.0, 2: 3600.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0}

    assert _power_zone_share_percent(zone_seconds, include_zones=(2,)) == 60.0


def test_power_zone_share_percent_distinguishes_z1_plus_z2_from_z2():
    zone_seconds = {1: 2400.0, 2: 1800.0, 3: 1800.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.0}

    assert _power_zone_share_percent(zone_seconds, include_zones=(2,)) == 30.0
    assert _power_zone_share_percent(zone_seconds, include_zones=(1, 2)) == 70.0


def test_power_zone_share_percent_returns_nan_without_zone_time():
    result = _power_zone_share_percent({}, include_zones=(2,))

    assert math.isnan(result)
