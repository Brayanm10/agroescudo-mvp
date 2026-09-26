from datetime import datetime, timezone

from scripts.seed_pluviometry_demo import (
    DEMO_ASSETS,
    DEMO_COMPANY,
    DEMO_DEVICE_IDS,
    DEMO_SITE,
    _demo_values,
)


def test_demo_topology_is_explicitly_labeled_and_separated():
    assert DEMO_COMPANY == "AgroEscudo Demo"
    assert DEMO_SITE.startswith("Demo ")
    assert len(DEMO_ASSETS) == len(DEMO_DEVICE_IDS) == 2
    assert all("DEMO" in asset["parcel"] for asset in DEMO_ASSETS)
    assert DEMO_ASSETS[0]["latitude"] != DEMO_ASSETS[1]["latitude"]
    assert DEMO_ASSETS[0]["longitude"] != DEMO_ASSETS[1]["longitude"]


def test_demo_weather_is_plausible_and_rain_remains_incremental():
    sampled_at = datetime(2026, 9, 18, tzinfo=timezone.utc)
    samples = [_demo_values(0, index, 673, sampled_at) for index in range(673)]
    rain = [sample["RAIN_DELTA_MM"] for sample in samples]
    assert min(rain) == 0
    assert 0 < max(rain) <= 3
    assert all(0 <= sample["AMBIENT_RELATIVE_HUMIDITY_PCT"] <= 100 for sample in samples)
    assert all(0 <= sample["BATTERY_PERCENT"] <= 100 for sample in samples)


def test_demo_wind_exercises_north_crossing_without_becoming_south():
    sampled_at = datetime(2026, 9, 18, tzinfo=timezone.utc)
    directions = [_demo_values(0, index, 673, sampled_at)["WIND_DIRECTION_DEG"] for index in range(669, 673)]
    assert directions == [359.0, 1.0, 5.0, 45.0]
