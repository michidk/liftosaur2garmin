"""Tests for sync orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


from liftosaur2garmin.sync import fetch_workout_hr_samples, fetch_workouts, sync


def _timestamp_ms(value: str) -> int:
    return round(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp() * 1000)


class TestFetchWorkoutHRSamples:
    def test_filters_sorts_and_validates_samples(self, sample_workout: dict) -> None:
        client = MagicMock()
        client.get_heart_rates.return_value = {
            "heartRateValues": [
                [_timestamp_ms("2026-04-01T20:30:00"), 130],
                [_timestamp_ms("2026-04-01T19:59:00"), 80],
                [_timestamp_ms("2026-04-01T20:10:00"), 110],
                [_timestamp_ms("2026-04-01T20:20:00"), None],
                [_timestamp_ms("2026-04-01T20:40:00"), 999],
            ]
        }

        result = fetch_workout_hr_samples(client, sample_workout)

        assert result == [110, 130]
        client.get_heart_rates.assert_called_once_with("2026-04-01")

    def test_fetches_both_days_for_workout_crossing_midnight(self) -> None:
        workout = {
            "start_time": "2026-04-01T23:55:00+00:00",
            "end_time": "2026-04-02T00:05:00+00:00",
        }
        midnight = _timestamp_ms("2026-04-02T00:00:00")
        client = MagicMock()
        client.get_heart_rates.side_effect = [
            {"heartRateValues": [[_timestamp_ms("2026-04-01T23:58:00"), 100], [midnight, 105]]},
            {"heartRateValues": [[midnight, 105], [_timestamp_ms("2026-04-02T00:03:00"), 110]]},
        ]

        result = fetch_workout_hr_samples(client, workout)

        assert result == [100, 105, 110]
        assert [call.args[0] for call in client.get_heart_rates.call_args_list] == ["2026-04-01", "2026-04-02"]

    def test_api_failure_falls_back_without_raising(self, sample_workout: dict) -> None:
        client = MagicMock()
        client.get_heart_rates.side_effect = RuntimeError("Garmin unavailable")

        assert fetch_workout_hr_samples(client, sample_workout) == []


class TestFetchWorkouts:
    def test_with_limit(self) -> None:
        client = MagicMock()
        client.get_workouts.return_value = {
            "workouts": [{"id": f"w{i}"} for i in range(5)],
            "page_count": 1,
        }
        result = fetch_workouts(client, limit=3)
        assert len(result) == 3

    def test_with_since_date(self) -> None:
        client = MagicMock()
        client.get_workouts.return_value = {
            "workouts": [
                {"id": "w1", "start_time": "2026-04-01T20:00:00+00:00"},
                {"id": "w2", "start_time": "2026-03-15T20:00:00+00:00"},
                {"id": "w3", "start_time": "2026-03-01T20:00:00+00:00"},
            ],
            "page_count": 1,
        }
        result = fetch_workouts(client, since="2026-03-10")
        assert len(result) == 2  # w1 and w2, w3 is before since

    def test_pagination(self) -> None:
        client = MagicMock()
        client.get_workouts.side_effect = [
            {"workouts": [{"id": "w1", "start_time": "2026-04-01"}], "page_count": 2},
            {"workouts": [{"id": "w2", "start_time": "2026-03-31"}], "page_count": 2},
        ]
        result = fetch_workouts(client, fetch_all=True)
        assert len(result) == 2

    def test_empty_response(self) -> None:
        client = MagicMock()
        client.get_workouts.return_value = {"workouts": [], "page_count": 0}
        result = fetch_workouts(client, fetch_all=True)
        assert result == []


class TestSync:
    def test_dry_run_no_garmin_calls(self, sample_workout: dict) -> None:
        with patch("liftosaur2garmin.sync.LiftosaurClient") as MockClient, \
             patch("liftosaur2garmin.sync.get_client") as mock_garmin, \
             patch("liftosaur2garmin.sync.db") as mock_db:
            mock_client = MockClient.return_value
            mock_client.get_workout_count.return_value = 1
            mock_client.get_workouts.return_value = {"workouts": [sample_workout], "page_count": 1}
            mock_db.is_synced.return_value = False

            result = sync(dry_run=True, limit=1, liftosaur_api_key="test")

            mock_garmin.assert_not_called()
            assert result["synced"] == 1

    def test_skips_already_synced(self, sample_workout: dict) -> None:
        with patch("liftosaur2garmin.sync.LiftosaurClient") as MockClient, \
             patch("liftosaur2garmin.sync.db") as mock_db, \
             patch("liftosaur2garmin.sync.get_client"):
            mock_client = MockClient.return_value
            mock_client.get_workout_count.return_value = 1
            mock_client.get_workouts.return_value = {"workouts": [sample_workout], "page_count": 1}
            mock_db.is_synced.return_value = True

            result = sync(dry_run=True, limit=1, liftosaur_api_key="test")
            assert result["skipped"] == 1
            assert result["synced"] == 0

    def test_reports_unmapped_exercises(self, sample_workout_unmapped: dict) -> None:
        with patch("liftosaur2garmin.sync.LiftosaurClient") as MockClient, \
             patch("liftosaur2garmin.sync.db") as mock_db, \
             patch("liftosaur2garmin.sync.get_client"):
            mock_client = MockClient.return_value
            mock_client.get_workout_count.return_value = 1
            mock_client.get_workouts.return_value = {"workouts": [sample_workout_unmapped], "page_count": 1}
            mock_db.is_synced.return_value = False

            result = sync(dry_run=True, limit=1, liftosaur_api_key="test")
            assert "Invented Exercise 99" in result["unmapped"]

    def test_handles_fit_generation_failure(self) -> None:
        bad_workout = {
            "id": "bad",
            "title": "Bad",
            "start_time": "invalid",
            "end_time": "also-invalid",
            "exercises": [],
        }
        with patch("liftosaur2garmin.sync.LiftosaurClient") as MockClient, \
             patch("liftosaur2garmin.sync.db") as mock_db, \
             patch("liftosaur2garmin.sync.get_client"):
            mock_client = MockClient.return_value
            mock_client.get_workout_count.return_value = 1
            mock_client.get_workouts.return_value = {"workouts": [bad_workout], "page_count": 1}
            mock_db.is_synced.return_value = False

            result = sync(dry_run=True, limit=1, liftosaur_api_key="test")
            assert result["failed"] == 1

    def test_records_to_db_after_success(self, sample_workout: dict) -> None:
        with patch("liftosaur2garmin.sync.LiftosaurClient") as MockClient, \
             patch("liftosaur2garmin.sync.db") as mock_db, \
             patch("liftosaur2garmin.sync.get_client"), \
             patch("liftosaur2garmin.sync.upload_fit") as mock_upload, \
             patch("liftosaur2garmin.sync.rename_activity"), \
             patch("liftosaur2garmin.sync.set_description"):
            mock_client = MockClient.return_value
            mock_client.get_workout_count.return_value = 1
            mock_client.get_workouts.return_value = {"workouts": [sample_workout], "page_count": 1}
            mock_db.is_synced.return_value = False
            mock_upload.return_value = {"upload_id": "123", "activity_id": 456}

            result = sync(limit=1, liftosaur_api_key="test", garmin_email="e", garmin_password="p")
            mock_db.mark_synced.assert_called_once()
            assert result["synced"] == 1

    def test_embeds_garmin_hr_in_uploaded_fit(self, sample_workout: dict) -> None:
        captured_hr: list[int] = []

        def fake_generate_fit(_workout, hr_samples, output_path):
            captured_hr.extend(hr_samples)
            return {"exercises": 2, "total_sets": 6, "calories": 321, "avg_hr": 120}

        with patch("liftosaur2garmin.sync.LiftosaurClient") as MockClient, \
             patch("liftosaur2garmin.sync.db") as mock_db, \
             patch("liftosaur2garmin.sync.get_client") as mock_get_client, \
             patch("liftosaur2garmin.sync.generate_fit", side_effect=fake_generate_fit), \
             patch("liftosaur2garmin.sync.upload_fit", return_value={"activity_id": 456}), \
             patch("liftosaur2garmin.sync.rename_activity"), \
             patch("liftosaur2garmin.sync.set_description"):
            source_client = MockClient.return_value
            source_client.get_workout_count.return_value = 1
            source_client.get_workouts.return_value = {"workouts": [sample_workout], "page_count": 1}
            mock_db.is_synced.return_value = False
            garmin_client = mock_get_client.return_value
            garmin_client.get_heart_rates.return_value = {
                "heartRateValues": [
                    [_timestamp_ms("2026-04-01T20:05:00"), 115],
                    [_timestamp_ms("2026-04-01T20:35:00"), 125],
                ]
            }

            result = sync(
                config={
                    "liftosaur_api_key": "test",
                    "garmin_email": "e",
                    "hr_fusion": {"enabled": True},
                    "update_existing": {"enabled": False},
                    "sync": {"skip_existing": True},
                },
                limit=1,
            )

        assert result["synced"] == 1
        assert captured_hr == [115, 125]
