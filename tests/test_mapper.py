"""Tests for exercise mapper."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fit_tool.profile.profile_type import ExerciseCategory

from liftosaur2garmin.liftosaur_mappings import LIFTOSAUR_CANONICAL_TO_GARMIN
from liftosaur2garmin.mapper import (
    EXERCISE_TO_GARMIN,
    _UNKNOWN_CATEGORY,
    lookup_exercise,
    _custom_mappings,
    _ensure_custom_loaded,
)


LIFTOSAUR_BUILTIN_NAMES = frozenset(
    line
    for line in (Path(__file__).parent / "fixtures" / "liftosaur_builtin_exercises.txt").read_text().splitlines()
    if line and not line.startswith("#")
)
INTENTIONAL_UNKNOWN_NAMES = frozenset(
    {
        "Arch Hang",
        "Crow Pose",
        "Dead Hang",
        "Handstand",
        "Leg Extension",
        "Squat Row",
        "Support Hold",
        "Torso Rotation",
        "Wall Handstand",
    }
)


class TestLookupBuiltIn:
    def test_known_exercise(self) -> None:
        cat, subcat, name = lookup_exercise("Bench Press (Barbell)")
        assert cat == 0
        assert subcat == 1
        assert name == "Bench Press (Barbell)"

    def test_squat(self) -> None:
        cat, subcat, name = lookup_exercise("Squat (Barbell)")
        assert cat == 28
        assert name == "Squat (Barbell)"

    def test_unknown_exercise(self) -> None:
        cat, subcat, name = lookup_exercise("Made Up Exercise 12345")
        assert cat == _UNKNOWN_CATEGORY
        assert subcat == 0
        assert name == "Made Up Exercise 12345"

    def test_empty_string(self) -> None:
        cat, subcat, name = lookup_exercise("")
        assert cat == _UNKNOWN_CATEGORY
        assert name == ""

    def test_mapping_count_minimum(self) -> None:
        assert len(EXERCISE_TO_GARMIN) >= 400

    def test_preserves_original_name(self) -> None:
        _, _, name = lookup_exercise("Deadlift (Barbell)")
        assert name == "Deadlift (Barbell)"

    @pytest.mark.parametrize(
        ("liftosaur_name", "expected"),
        [
            ("Elliptical Machine", (39, 0)),
            ("Deadlift, Cable", (8, 0)),
            ("Lat Pulldown", (21, 13)),
            ("Seated Row", (23, 18)),
            ("Lateral Raise", (14, 34)),
            ("Bicep Curl", (7, 46)),
            ("Triceps Extension", (30, 15)),
        ],
    )
    def test_maps_live_liftosaur_names(self, liftosaur_name: str, expected: tuple[int, int]) -> None:
        assert lookup_exercise(liftosaur_name)[:2] == expected

    def test_all_liftosaur_builtins_have_reviewed_mappings(self) -> None:
        unknown = {
            name
            for name in LIFTOSAUR_BUILTIN_NAMES
            if lookup_exercise(name)[0] == _UNKNOWN_CATEGORY
        }
        assert unknown == INTENTIONAL_UNKNOWN_NAMES

    def test_canonical_mapping_matches_pinned_liftosaur_catalog(self) -> None:
        assert frozenset(LIFTOSAUR_CANONICAL_TO_GARMIN) == LIFTOSAUR_BUILTIN_NAMES

    def test_all_liftosaur_builtin_categories_exist_in_fit_profile(self) -> None:
        current_fit_categories = {
            *{category.value for category in ExerciseCategory},
            33,
            38,
            39,
            42,
        }
        invalid = {
            name: lookup_exercise(name)[0]
            for name in LIFTOSAUR_BUILTIN_NAMES
            if lookup_exercise(name)[0] not in current_fit_categories
        }
        assert invalid == {}

    def test_overhead_lunge_and_carry_have_distinct_mappings(self) -> None:
        assert lookup_exercise("Overhead Dumbbell Lunge")[:2] == (17, 40)
        assert lookup_exercise("Overhead Carry")[:2] == (3, 4)

    def test_semantically_risky_canonical_mappings(self) -> None:
        expected = {
            "Battle Ropes": (38, 5),
            "Bicep Curl": (7, 46),
            "Concentration Curl": (7, 44),
            "Copenhagen Plank": (19, 74),
            "Cycling": (33, 0),
            "Elliptical Machine": (39, 0),
            "Front Lever Row": (23, 26),
            "Kettlebell Turkish Get Up": (5, 89),
            "Lateral Raise": (14, 34),
            "Lateral Box Jump": (20, 13),
            "Lying Bicep Curl": (7, 46),
            "Pallof Press": (5, 6),
            "Rowing": (42, 0),
            "Scapular Pull Up": (26, 11),
            "Snatch": (18, 25),
            "Split Squat": (28, 28),
            "Vertical Row": (23, 10),
        }
        assert {name: lookup_exercise(name)[:2] for name in expected} == expected

    def test_equipment_qualified_names_fall_back_to_canonical_mapping(self) -> None:
        expected = {
            "Bicep Curl, Dumbbell": (7, 37),
            "Deadlift, Cable": (8, 0),
            "Lat Pulldown, Cable": (21, 13),
            "Seated Row, Leverage Machine": (23, 18),
            "Triceps Extension, Dumbbell": (30, 15),
        }
        assert {name: lookup_exercise(name)[:2] for name in expected} == expected


class TestCustomMappings:
    def test_custom_overrides_builtin(self, tmp_path: Path) -> None:
        mappings_file = tmp_path / "custom_mappings.json"
        mappings_file.write_text(json.dumps({"Bench Press (Barbell)": [99, 88]}))

        # Reset custom state
        _custom_mappings.clear()
        import liftosaur2garmin.mapper as m
        m._custom_loaded = False

        with patch.object(Path, "expanduser", return_value=mappings_file):
            with patch("liftosaur2garmin.mapper._custom_loaded", False):
                # Force reload
                m._custom_loaded = False
                m._custom_mappings.clear()
                m._custom_mappings["Bench Press (Barbell)"] = (99, 88)
                cat, subcat, _ = lookup_exercise("Bench Press (Barbell)")
                assert cat == 99
                assert subcat == 88

        # Cleanup
        m._custom_mappings.clear()

    def test_custom_does_not_affect_other_exercises(self) -> None:
        import liftosaur2garmin.mapper as m
        m._custom_mappings["Only This One"] = (1, 2)
        cat, _, _ = lookup_exercise("Squat (Barbell)")
        assert cat == 28  # unchanged
        m._custom_mappings.clear()

    def test_save_custom_mapping_in_memory(self) -> None:
        import liftosaur2garmin.mapper as m
        m._custom_mappings["Test Exercise"] = (5, 10)
        cat, subcat, _ = lookup_exercise("Test Exercise")
        assert cat == 5
        assert subcat == 10
        m._custom_mappings.clear()

    def test_missing_custom_file_no_crash(self) -> None:
        import liftosaur2garmin.mapper as m
        m._custom_loaded = False
        m._custom_mappings.clear()
        # Should not crash when file doesn't exist
        _ensure_custom_loaded()

    def test_cloud_mapping_save_updates_lookup_without_reload(self, monkeypatch) -> None:
        import liftosaur2garmin.mapper as m
        from liftosaur2garmin import server

        class FakeDb:
            def __init__(self) -> None:
                self.saved: list[tuple[str, int, int]] = []

            def save_custom_mapping(self, name: str, category: int, subcategory: int) -> None:
                self.saved.append((name, category, subcategory))

        fake_db = FakeDb()
        m._custom_loaded = True
        m._custom_mappings.clear()
        server._is_configured_cache = True
        monkeypatch.setattr(server.db, "get_database_url", lambda: "postgres://example")
        monkeypatch.setattr(server.db, "get_db", lambda: fake_db)

        from fastapi.testclient import TestClient

        client = TestClient(server.app)
        response = client.post(
            "/api/mapping",
            data={"exercise_name": "Cloud Only Exercise", "category": "7", "subcategory": "3"},
        )

        assert response.status_code == 200
        assert fake_db.saved == [("Cloud Only Exercise", 7, 3)]
        assert lookup_exercise("Cloud Only Exercise")[:2] == (7, 3)
