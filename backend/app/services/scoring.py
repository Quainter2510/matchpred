"""Pure scoring functions. No side effects, no I/O — fully unit-testable.

Only main time (90 min) scores are ever passed in. Extra time and penalties
are not represented anywhere in the system.

Scoring table:
    Exact score  (both goals match)               -> 5
    Goal difference (diff and winner match)        -> 2
    Outcome (sign of result matches)               -> 1
    Miss                                            -> 0
"""
from __future__ import annotations

POINTS_EXACT = 5
POINTS_DIFF = 2
POINTS_OUTCOME = 1
POINTS_MISS = 0

POINTS_CHAMPION = 10
POINTS_TOP_SCORER = 10


def _sign(value: int) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def score_prediction(
    predicted_home: int,
    predicted_away: int,
    actual_home: int,
    actual_away: int,
) -> tuple[int, bool]:
    """Return (points, is_exact) for a single match prediction.

    >>> score_prediction(2, 1, 2, 1)
    (5, True)
    """
    is_exact = predicted_home == actual_home and predicted_away == actual_away
    if is_exact:
        return POINTS_EXACT, True

    pred_diff = predicted_home - predicted_away
    actual_diff = actual_home - actual_away

    # Goal difference: same difference AND same winner (sign matches implicitly
    # when the diffs are equal and non-zero; for a 0 diff that means a draw).
    if pred_diff == actual_diff:
        return POINTS_DIFF, False

    # Outcome: the sign of the result matches (win/draw/loss).
    if _sign(pred_diff) == _sign(actual_diff):
        return POINTS_OUTCOME, False

    return POINTS_MISS, False


def determine_winner(home_team: str, away_team: str, home_score: int, away_score: int) -> str | None:
    """Return the winning team name, or None for a draw."""
    if home_score > away_score:
        return home_team
    if away_score > home_score:
        return away_team
    return None
