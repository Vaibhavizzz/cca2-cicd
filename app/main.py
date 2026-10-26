"""
Student Grade Management System
Flask application entry point.
"""
import os
import socket

from flask import Flask, jsonify, render_template, abort

from app import grades, data

# ---------------------------------------------------------------------------
# CHANGE THIS STRING FOR THE SECOND PIPELINE RUN.
# It is rendered in the page banner, so the redeployment is visible in a browser
# rather than only in kubectl output. This is the evidence for requirement 9.
# ---------------------------------------------------------------------------
APP_VERSION = "v1.1"
RELEASE_NOTE = "Initial release"

app = Flask(__name__)


@app.context_processor
def inject_globals():
    """Make build metadata available to every template."""
    return {
        "app_version": APP_VERSION,
        "release_note": RELEASE_NOTE,
        # Set by Kubernetes from the Downward API would be nicer, but the pod
        # hostname is already unique per pod and proves load balancing works.
        "pod_name": os.environ.get("HOSTNAME", socket.gethostname()),
        "build_number": os.environ.get("BUILD_NUMBER", "local"),
    }


@app.route("/")
def index():
    records = [grades.summarise(s) for s in data.all_students()]
    records.sort(key=lambda r: r["sgpa"], reverse=True)
    return render_template("index.html", students=records)


@app.route("/student/<roll_no>")
def student_detail(roll_no):
    student = data.find_student(roll_no)
    if student is None:
        abort(404)
    return render_template("detail.html", student=grades.summarise(student))


# --------------------------- JSON API ---------------------------

@app.route("/api/students")
def api_students():
    return jsonify([grades.summarise(s) for s in data.all_students()])


@app.route("/api/students/<roll_no>")
def api_student(roll_no):
    student = data.find_student(roll_no)
    if student is None:
        return jsonify({"error": "student not found", "roll_no": roll_no}), 404
    return jsonify(grades.summarise(student))


@app.route("/api/grade/<int:score>")
def api_grade(score):
    """Convenience endpoint: convert a raw score to its grade."""
    try:
        return jsonify({
            "score": score,
            "grade": grades.letter_grade(score),
            "points": grades.grade_point(score),
            "passed": grades.has_passed(score),
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/health")
def health():
    """Liveness endpoint. Kept trivial so it never depends on app state."""
    return jsonify({"status": "ok", "version": APP_VERSION}), 200


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    # Development server only. The container runs gunicorn instead.
    app.run(host="0.0.0.0", port=5000, debug=True)
