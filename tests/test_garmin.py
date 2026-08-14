"""Tests for Garmin upload module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from liftosaur2garmin.garmin import (
    GarminAuthSession,
    GarminConnectAuthenticationError,
    find_activity_by_start_time,
    generate_description,
    get_client,
)


class TestGarminTokenRefresh:
    def test_rotated_refresh_token_is_persisted_for_next_client(self, tmp_path, monkeypatch) -> None:
        token_file = tmp_path / "garmin_tokens.json"
        token_file.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "garmin_native_auth",
                    "email": "user@example.com",
                    "auth": {
                        "di_token": "expired-access-token",
                        "di_refresh_token": "old-refresh-token",
                        "di_client_id": "client-id",
                    },
                }
            )
        )

        refresh_response = MagicMock(status_code=200, ok=True)
        refresh_response.json.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
        }
        api_response = MagicMock(status_code=200)

        monkeypatch.setattr("liftosaur2garmin.db.get_database_url", lambda: None)
        monkeypatch.setattr("liftosaur2garmin.garmin.requests.post", lambda *_args, **_kwargs: refresh_response)
        monkeypatch.setattr("liftosaur2garmin.garmin.requests.request", lambda *_args, **_kwargs: api_response)
        monkeypatch.setattr(GarminAuthSession, "_token_expires_soon", lambda _self: True)

        first_client = get_client(token_dir=str(token_file))
        first_client.auth.request("GET", "/test")

        persisted = json.loads(token_file.read_text())
        assert persisted["email"] == "user@example.com"
        assert persisted["auth"]["di_token"] == "new-access-token"
        assert persisted["auth"]["di_refresh_token"] == "new-refresh-token"

        next_client = get_client(token_dir=str(token_file))
        assert next_client.auth.di_token == "new-access-token"
        assert next_client.auth.di_refresh_token == "new-refresh-token"

    def test_refresh_failure_does_not_expose_token_response(self, monkeypatch) -> None:
        response = MagicMock(
            status_code=400,
            ok=False,
            text='{"error":"invalid_grant","error_description":"Invalid refresh token: secret-token"}',
        )
        monkeypatch.setattr("liftosaur2garmin.garmin.requests.post", lambda *_args, **_kwargs: response)

        auth = GarminAuthSession()
        auth.di_token = "expired-access-token"
        auth.di_refresh_token = "secret-token"
        auth.di_client_id = "client-id"

        with pytest.raises(GarminConnectAuthenticationError) as exc_info:
            auth._refresh_di_token()

        assert str(exc_info.value) == "Garmin token refresh failed: HTTP 400"
        assert "secret-token" not in str(exc_info.value)


class TestFindActivityByStartTime:
    def _make_activities(self, *start_times: str) -> list[dict]:
        return [
            {"activityId": i + 1, "startTimeLocal": t}
            for i, t in enumerate(start_times)
        ]

    def test_exact_match(self) -> None:
        client = MagicMock()
        acts = self._make_activities("2026-04-01 20:00:00")
        with patch("liftosaur2garmin.garmin._limiter") as mock_limiter:
            mock_limiter.call.return_value = acts
            result = find_activity_by_start_time(client, "2026-04-01T20:00:00+00:00")
            assert result == 1

    def test_within_window(self) -> None:
        client = MagicMock()
        acts = self._make_activities("2026-04-01 20:05:00")
        with patch("liftosaur2garmin.garmin._limiter") as mock_limiter:
            mock_limiter.call.return_value = acts
            result = find_activity_by_start_time(client, "2026-04-01T20:00:00+00:00", window_minutes=10)
            assert result == 1

    def test_outside_window(self) -> None:
        client = MagicMock()
        acts = self._make_activities("2026-04-01 21:00:00")
        with patch("liftosaur2garmin.garmin._limiter") as mock_limiter:
            mock_limiter.call.return_value = acts
            result = find_activity_by_start_time(client, "2026-04-01T20:00:00+00:00", window_minutes=10)
            assert result is None

    def test_no_activities(self) -> None:
        client = MagicMock()
        with patch("liftosaur2garmin.garmin._limiter") as mock_limiter:
            mock_limiter.call.return_value = []
            result = find_activity_by_start_time(client, "2026-04-01T20:00:00+00:00")
            assert result is None

    def test_picks_closest(self) -> None:
        client = MagicMock()
        acts = self._make_activities("2026-04-01 21:00:00", "2026-04-01 20:02:00")
        with patch("liftosaur2garmin.garmin._limiter") as mock_limiter:
            mock_limiter.call.return_value = acts
            result = find_activity_by_start_time(client, "2026-04-01T20:00:00+00:00", window_minutes=10)
            assert result == 2  # the 20:02 one

    def test_invalid_target_time(self) -> None:
        client = MagicMock()
        result = find_activity_by_start_time(client, "not-a-date")
        assert result is None

    def test_api_error_returns_none(self) -> None:
        client = MagicMock()
        with patch("liftosaur2garmin.garmin._limiter") as mock_limiter:
            mock_limiter.call.side_effect = Exception("API error")
            result = find_activity_by_start_time(client, "2026-04-01T20:00:00+00:00")
            assert result is None


class TestGenerateDescription:
    def test_basic_description(self, sample_workout: dict) -> None:
        desc = generate_description(sample_workout, calories=200, avg_hr=95)
        assert "🏋️ Push" in desc
        assert "200 kcal" in desc
        assert "avg 95 bpm" in desc
        assert "liftosaur2garmin" in desc

    def test_includes_exercises(self, sample_workout: dict) -> None:
        desc = generate_description(sample_workout)
        assert "Bench Press" in desc
        assert "Shoulder Press" in desc

    def test_shows_sets_and_weight(self, sample_workout: dict) -> None:
        desc = generate_description(sample_workout)
        assert "3 sets" in desc  # 3 normal bench sets
        assert "60.0kg" in desc

    def test_no_calories(self, sample_workout: dict) -> None:
        desc = generate_description(sample_workout, calories=None, avg_hr=None)
        assert "kcal" not in desc
        assert "bpm" not in desc

    def test_duration(self, sample_workout: dict) -> None:
        desc = generate_description(sample_workout)
        assert "45 min" in desc

    def test_empty_workout(self) -> None:
        workout = {"title": "Empty", "exercises": []}
        desc = generate_description(workout)
        assert "Empty" in desc
