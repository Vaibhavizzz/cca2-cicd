"""Unit tests for the grade computation logic."""
import pytest

from app import grades


class TestLetterGrade:

    @pytest.mark.parametrize("score,expected", [
        (100, "O"), (95, "O"), (90, "O"),
        (89, "A+"), (80, "A+"),
        (79, "A"), (70, "A"),
        (69, "B+"), (60, "B+"),
        (59, "B"), (50, "B"),
        (49, "C"), (45, "C"),
        (44, "P"), (40, "P"),
        (39, "F"), (0, "F"),
    ])
    def test_band_boundaries(self, score, expected):
        assert grades.letter_grade(score) == expected

    def test_accepts_float(self):
        assert grades.letter_grade(89.9) == "A+"

    def test_accepts_numeric_string(self):
        assert grades.letter_grade("75") == "A"


class TestGradePoint:

    @pytest.mark.parametrize("score,expected", [
        (92, 10), (85, 9), (74, 8), (63, 7), (52, 6), (46, 5), (41, 4), (12, 0),
    ])
    def test_points(self, score, expected):
        assert grades.grade_point(score) == expected


class TestValidation:

    @pytest.mark.parametrize("bad", [-1, 101, 150, -0.5])
    def test_out_of_range_rejected(self, bad):
        with pytest.raises(ValueError):
            grades.validate_score(bad)

    @pytest.mark.parametrize("bad", ["abc", None, "", [1]])
    def test_non_numeric_rejected(self, bad):
        with pytest.raises(ValueError):
            grades.validate_score(bad)

    def test_bounds_are_inclusive(self):
        assert grades.validate_score(0) == 0.0
        assert grades.validate_score(100) == 100.0


class TestHasPassed:

    def test_exactly_at_pass_mark_passes(self):
        assert grades.has_passed(40) is True

    def test_just_below_pass_mark_fails(self):
        assert grades.has_passed(39) is False


class TestCalculateSgpa:

    def test_empty_list_is_zero(self):
        assert grades.calculate_sgpa([]) == 0.0

    def test_single_course(self):
        # 92 -> 10 points, so SGPA is 10.0 regardless of credits
        assert grades.calculate_sgpa([{"credits": 4, "score": 92}]) == 10.0

    def test_credit_weighting_applies(self):
        # (10*4 + 6*2) / 6 = 52/6 = 8.666... -> 8.67
        courses = [
            {"credits": 4, "score": 95},   # 10 points
            {"credits": 2, "score": 55},   # 6 points
        ]
        assert grades.calculate_sgpa(courses) == 8.67

    def test_all_failures_give_zero(self):
        courses = [{"credits": 4, "score": 10}, {"credits": 3, "score": 0}]
        assert grades.calculate_sgpa(courses) == 0.0

    @pytest.mark.parametrize("bad_credits", [0, -2, "four", None])
    def test_invalid_credits_rejected(self, bad_credits):
        with pytest.raises(ValueError):
            grades.calculate_sgpa([{"credits": bad_credits, "score": 70}])


class TestSummarise:

    def test_builds_full_record(self):
        student = {
            "roll_no": "CS22001",
            "name": "Test Student",
            "courses": [
                {"code": "CS301", "title": "OS", "credits": 4, "score": 88},
                {"code": "CS302", "title": "CN", "credits": 3, "score": 35},
            ],
        }
        result = grades.summarise(student)

        assert result["roll_no"] == "CS22001"
        assert result["total_credits"] == 7
        assert result["courses"][0]["grade"] == "A+"
        assert result["courses"][1]["grade"] == "F"
        assert result["all_cleared"] is False

    def test_all_cleared_true_when_every_course_passed(self):
        student = {
            "roll_no": "CS22002",
            "name": "Another Student",
            "courses": [{"code": "CS301", "title": "OS", "credits": 4, "score": 55}],
        }
        assert grades.summarise(student)["all_cleared"] is True
