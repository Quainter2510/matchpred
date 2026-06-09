import pytest

from app.services.scoring import (
    POINTS_DIFF,
    POINTS_EXACT,
    POINTS_MISS,
    POINTS_OUTCOME,
    determine_winner,
    score_prediction,
)


class TestExactScore:
    def test_exact_home_win(self):
        assert score_prediction(2, 1, 2, 1) == (POINTS_EXACT, True)

    def test_exact_draw(self):
        assert score_prediction(0, 0, 0, 0) == (POINTS_EXACT, True)

    def test_exact_away_win(self):
        assert score_prediction(1, 3, 1, 3) == (POINTS_EXACT, True)


class TestGoalDifference:
    def test_same_diff_home_win(self):
        # predicted 2:1 (diff +1), actual 3:2 (diff +1) -> 2 points
        assert score_prediction(2, 1, 3, 2) == (POINTS_DIFF, False)

    def test_same_diff_away_win(self):
        # predicted 1:2 (diff -1), actual 0:1 (diff -1) -> 2 points
        assert score_prediction(1, 2, 0, 1) == (POINTS_DIFF, False)

    def test_draw_non_exact_is_diff(self):
        # predicted 1:1 (draw), actual 2:2 (draw) -> diff 0 == 0 -> 2 points
        assert score_prediction(1, 1, 2, 2) == (POINTS_DIFF, False)


class TestOutcome:
    def test_home_win_wrong_diff(self):
        # predicted 3:0 (+3 home win), actual 1:0 (+1 home win) -> outcome only
        assert score_prediction(3, 0, 1, 0) == (POINTS_OUTCOME, False)

    def test_away_win_wrong_diff(self):
        assert score_prediction(0, 3, 1, 2) == (POINTS_OUTCOME, False)


class TestMiss:
    def test_predicted_win_actual_loss(self):
        assert score_prediction(2, 0, 0, 2) == (POINTS_MISS, False)

    def test_predicted_draw_actual_win(self):
        # predicted 1:1 (draw), actual 2:0 (home win) -> miss
        assert score_prediction(1, 1, 2, 0) == (POINTS_MISS, False)

    def test_predicted_win_actual_draw(self):
        assert score_prediction(2, 1, 0, 0) == (POINTS_MISS, False)


class TestDetermineWinner:
    def test_home(self):
        assert determine_winner("A", "B", 2, 1) == "A"

    def test_away(self):
        assert determine_winner("A", "B", 0, 1) == "B"

    def test_draw(self):
        assert determine_winner("A", "B", 1, 1) is None


@pytest.mark.parametrize(
    "ph,pa,ah,aa,expected_points,expected_exact",
    [
        (2, 1, 2, 1, 5, True),
        (2, 1, 3, 2, 2, False),
        (3, 0, 1, 0, 1, False),
        (2, 0, 0, 2, 0, False),
        (0, 0, 0, 0, 5, True),
        (1, 1, 2, 2, 2, False),
        (1, 1, 2, 0, 0, False),
    ],
)
def test_scoring_table(ph, pa, ah, aa, expected_points, expected_exact):
    assert score_prediction(ph, pa, ah, aa) == (expected_points, expected_exact)
