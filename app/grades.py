"""
Grade computation logic for the Student Grade Management System.

This module is deliberately kept free of Flask imports so it can be unit tested
on its own. Those unit tests are what the Jenkins "Build & Test" stage runs.
"""

# Marks banding used by the department. Checked in descending order.
GRADE_BANDS = [
    (90, "O",  10),   # (minimum score, letter, grade point)
    (80, "A+",  9),
    (70, "A",   8),
    (60, "B+",  7),
    (50, "B",   6),
    (45, "C",   5),
    (40, "P",   4),
    (0,  "F",   0),
]

PASS_MARK = 40


def validate_score(score):
    """Return the score as a float, or raise ValueError if it is not 0-100."""
    try:
        value = float(score)
    except (TypeError, ValueError):
        raise ValueError("score must be a number")
    if value < 0 or value > 100:
        raise ValueError("score must be between 0 and 100")
    return value


def letter_grade(score):
    """Map a numeric score to its letter grade."""
    value = validate_score(score)
    for minimum, letter, _points in GRADE_BANDS:
        if value >= minimum:
            return letter
    return "F"


def grade_point(score):
    """Map a numeric score to its grade point on the 10 point scale."""
    value = validate_score(score)
    for minimum, _letter, points in GRADE_BANDS:
        if value >= minimum:
            return points
    return 0


def has_passed(score):
    """True if the score clears the pass mark."""
    return validate_score(score) >= PASS_MARK


def calculate_sgpa(courses):
    """
    Credit weighted semester grade point average.

    courses: list of dicts, each with "credits" and "score".
    Returns a float rounded to two decimals. An empty list gives 0.0.
    """
    if not courses:
        return 0.0

    total_credits = 0
    weighted_points = 0

    for course in courses:
        credits = course.get("credits")
        if not isinstance(credits, (int, float)) or credits <= 0:
            raise ValueError("credits must be a positive number")
        points = grade_point(course.get("score"))
        weighted_points += points * credits
        total_credits += credits

    if total_credits == 0:
        return 0.0

    return round(weighted_points / total_credits, 2)


def summarise(student):
    """
    Build the display record for one student.

    Expects a dict with "roll_no", "name" and "courses".
    """
    courses = student.get("courses", [])
    sgpa = calculate_sgpa(courses)

    detailed = []
    for course in courses:
        score = course["score"]
        detailed.append({
            "code": course.get("code", ""),
            "title": course.get("title", ""),
            "credits": course.get("credits", 0),
            "score": score,
            "grade": letter_grade(score),
            "points": grade_point(score),
            "passed": has_passed(score),
        })

    return {
        "roll_no": student.get("roll_no"),
        "name": student.get("name"),
        "courses": detailed,
        "sgpa": sgpa,
        "total_credits": sum(c.get("credits", 0) for c in courses),
        "all_cleared": all(c["passed"] for c in detailed) if detailed else False,
    }
