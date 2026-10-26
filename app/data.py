"""
Seed data for the Student Grade Management System.

Held in memory on purpose. The application is stateless, which is why it is safe
to run two replicas behind one Service without a shared volume or database.
This is a deliberate design choice worth explaining in the viva.
"""

STUDENTS = [
    {
        "roll_no": "CS22001",
        "name": "Aarav Mehta",
        "courses": [
            {"code": "CS301", "title": "Operating Systems",       "credits": 4, "score": 88},
            {"code": "CS302", "title": "Computer Networks",       "credits": 4, "score": 76},
            {"code": "CS303", "title": "Database Systems",        "credits": 3, "score": 92},
            {"code": "CS304", "title": "Cloud Computing",         "credits": 3, "score": 81},
        ],
    },
    {
        "roll_no": "CS22014",
        "name": "Ishita Rao",
        "courses": [
            {"code": "CS301", "title": "Operating Systems",       "credits": 4, "score": 65},
            {"code": "CS302", "title": "Computer Networks",       "credits": 4, "score": 58},
            {"code": "CS303", "title": "Database Systems",        "credits": 3, "score": 71},
            {"code": "CS304", "title": "Cloud Computing",         "credits": 3, "score": 69},
        ],
    },
    {
        "roll_no": "CS22027",
        "name": "Kabir Sheikh",
        "courses": [
            {"code": "CS301", "title": "Operating Systems",       "credits": 4, "score": 47},
            {"code": "CS302", "title": "Computer Networks",       "credits": 4, "score": 38},
            {"code": "CS303", "title": "Database Systems",        "credits": 3, "score": 55},
            {"code": "CS304", "title": "Cloud Computing",         "credits": 3, "score": 61},
        ],
    },
    {
        "roll_no": "CS22039",
        "name": "Meera Nair",
        "courses": [
            {"code": "CS301", "title": "Operating Systems",       "credits": 4, "score": 95},
            {"code": "CS302", "title": "Computer Networks",       "credits": 4, "score": 90},
            {"code": "CS303", "title": "Database Systems",        "credits": 3, "score": 86},
            {"code": "CS304", "title": "Cloud Computing",         "credits": 3, "score": 93},
        ],
    },
]


def all_students():
    return list(STUDENTS)


def find_student(roll_no):
    for student in STUDENTS:
        if student["roll_no"].upper() == str(roll_no).upper():
            return student
    return None
