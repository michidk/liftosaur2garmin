"""Garmin FIT fallbacks for exercise variants Strava does not recognize.

Garmin Connect can display the original Liftosaur title from an
``exercise_title`` message. Strava's FIT importer instead classifies strength
sets from their numeric ``category`` and ``category_subtype`` fields. A few
valid Garmin variants currently arrive in Strava as ``Unknown Exercise``.

These fallbacks keep each exercise in the same movement and muscle group while
using a broader FIT variant that Strava recognizes. The original title remains
unchanged in Garmin Connect.

References:
    https://developers.strava.com/docs/uploads/
    https://developers.strava.com/docs/changelog/
"""

from __future__ import annotations

from typing import Final


# Applied after the canonical Liftosaur mappings. Custom user mappings still
# take precedence because mapper.lookup_exercise checks them before this table.
STRAVA_COMPATIBLE_GARMIN_MAPPINGS: Final[dict[str, tuple[int, int]]] = {
    # military_press (24:25) -> overhead_barbell_press
    "Military Press": (24, 14),
    "Military Press (Barbell)": (24, 14),
    "Standing Military Press (Barbell)": (24, 14),

    # weighted_pull_up (21:24) -> pull_up. Set weight is still preserved.
    "Pull Up (Weighted)": (21, 38),
    "Weighted Pull Up": (21, 38),
    "Weighted Pull-up": (21, 38),

    # dumbbell_lateral_raise (14:34) -> seated_lateral_raise
    "Dumbbell Lateral Raise": (14, 24),
    "Lateral Raise": (14, 24),
    "Lateral Raise (Dumbbell)": (14, 24),

    # incline_reverse_flye (9:11) -> kneeling_rear_flye
    "Incline Reverse Fly": (9, 5),
    "Incline Reverse Fly (Dumbbell)": (9, 5),

    # hanging_leg_raise (16:1) -> hanging_knee_raise
    "Hanging Leg Raise": (16, 0),
    "Hanging Leg Raise (Weighted)": (16, 0),
    "Weighted Hanging Leg Raise": (16, 0),
}
