"""Garmin FIT fallbacks for exercise variants Strava does not recognize.

Generated FIT files contain the original Liftosaur title in an
``exercise_title`` message and numeric exercise pairs on both titles and sets.
Garmin Connect recognizes the pairs below, but they have been observed arriving
in Strava as ``Unknown``.

In one Garmin-to-Strava activity, the five consecutive unknown Strava sets had
the same repetitions as three ``dumbbell_lateral_raise`` sets followed by two
``dumbbell_biceps_curl`` sets in Garmin Connect. Strava's published strength
exercise list omits those two enum names but includes
``SEATED_DUMBBELL_LATERAL_RAISE`` and
``STANDING_DUMBBELL_BICEPS_CURL``. These fallbacks therefore use the matching
older FIT variants. The original Liftosaur title remains encoded in the FIT
file, although Garmin and Strava may display their taxonomy's variant name.

References:
    https://developers.strava.com/docs/uploads/
    https://developers.strava.com/docs/changelog/
"""

from __future__ import annotations

from typing import Final


# Applied after the canonical Liftosaur mappings. Custom user mappings still
# take precedence because mapper.lookup_exercise checks them first.
STRAVA_COMPATIBLE_GARMIN_PAIRS: Final[dict[tuple[int, int], tuple[int, int]]] = {
    # dumbbell_lateral_raise (14:34) -> seated_lateral_raise
    (14, 34): (14, 24),

    # dumbbell_biceps_curl (7:46) -> standing_dumbbell_biceps_curl
    (7, 46): (7, 37),
}
