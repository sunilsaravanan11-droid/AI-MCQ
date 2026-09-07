"""
app.py
AI MCQ Generator - Flask application entry point.

Flow: Upload PDF -> Select Topic -> Generate MCQs -> Take Quiz -> Get Score -> Streak
"""

import json
import os
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

from database import init_db, get_db
from services.pdf_service import extract_text_from_pdf, find_relevant_excerpt
from services.ai_service import detect_topics, generate_mcqs, AIServiceError
from services.streak_service import get_streak_info, record_study_session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join("/tmp", "uploads")
ALLOWED_EXTENSIONS = {"pdf"}

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB max upload

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
init_db()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    db = get_db()

    documents = db.execute(
        "SELECT id, filename, uploaded_at FROM documents ORDER BY id DESC LIMIT 5"
    ).fetchall()

    recent_attempt = db.execute(
        "SELECT * FROM attempts ORDER BY id DESC LIMIT 1"
    ).fetchone()

    db.close()

    streak = get_streak_info()

    return render_template(
        "index.html",
        documents=documents,
        recent_attempt=recent_attempt,
        streak=streak,
    )


# ---------------------------------------------------------------------------
# 1. PDF Upload
# ---------------------------------------------------------------------------

@app.route("/upload", methods=["POST"])
def upload_pdf():

    if "pdf_file" not in request.files:
        flash("No file was selected.", "error")
        return redirect(url_for("dashboard"))

    file = request.files["pdf_file"]

    if file.filename == "":
        flash("No file was selected.", "error")
        return redirect(url_for("dashboard"))

    if not allowed_file(file.filename):
        flash("Please upload a PDF file.", "error")
        return redirect(url_for("dashboard"))

    safe_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        safe_name
    )

    file.save(filepath)

    try:

        full_text = extract_text_from_pdf(filepath)

        if not full_text or len(full_text.strip()) < 50:
            flash(
                "Could not extract readable text from this PDF. Try another file.",
                "error"
            )
            return redirect(url_for("dashboard"))

        topics = detect_topics(full_text)

    except AIServiceError as exc:

        flash(
            f"AI error while analyzing the PDF: {exc}",
            "error"
        )

        return redirect(url_for("dashboard"))

    except Exception as exc:

        flash(
            f"Could not process this PDF: {exc}",
            "error"
        )

        return redirect(url_for("dashboard"))

    db = get_db()

    cursor = db.execute(
        "INSERT INTO documents (filename, full_text, topics, uploaded_at) "
        "VALUES (?, ?, ?, ?)",
        (
            file.filename,
            full_text,
            json.dumps(topics),
            datetime.now().isoformat()
        ),
    )

    db.commit()

    document_id = cursor.lastrowid

    db.close()

    return redirect(
        url_for(
            "select_topic",
            document_id=document_id
        )
    )


# ---------------------------------------------------------------------------
# 2. Topic selection + MCQ generator
# ---------------------------------------------------------------------------

@app.route("/document/<int:document_id>/topics")
def select_topic(document_id):

    db = get_db()

    document = db.execute(
        "SELECT * FROM documents WHERE id = ?",
        (document_id,)
    ).fetchone()

    db.close()

    if document is None:

        flash(
            "Document not found.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    topics = json.loads(
        document["topics"]
    )

    return render_template(
        "topics.html",
        document=document,
        topics=topics
    )


@app.route("/generate_quiz", methods=["POST"])
def generate_quiz():

    document_id = request.form.get(
        "document_id",
        type=int
    )

    topic = request.form.get(
        "topic",
        ""
    ).strip()

    num_questions = request.form.get(
        "num_questions",
        type=int,
        default=5
    )

    difficulty = request.form.get(
        "difficulty",
        "Medium"
    ).strip()

    if num_questions not in (5, 10, 15, 20):
        num_questions = 5

    if difficulty not in ("Easy", "Medium", "Hard"):
        difficulty = "Medium"

    db = get_db()

    document = db.execute(
        "SELECT * FROM documents WHERE id = ?",
        (document_id,)
    ).fetchone()

    if document is None or not topic:

        db.close()

        flash(
            "Please select a valid document and topic.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    excerpt = find_relevant_excerpt(
        document["full_text"],
        topic
    )

    try:

        questions = generate_mcqs(
            excerpt,
            topic,
            num_questions,
            difficulty
        )

    except AIServiceError as exc:

        db.close()

        flash(
            f"AI error while generating questions: {exc}",
            "error"
        )

        return redirect(
            url_for(
                "select_topic",
                document_id=document_id
            )
        )

    cursor = db.execute(
        "INSERT INTO quizzes "
        "(document_id, topic, difficulty, num_questions, questions_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            document_id,
            topic,
            difficulty,
            len(questions),
            json.dumps(questions),
            datetime.now().isoformat()
        ),
    )

    db.commit()

    quiz_id = cursor.lastrowid

    db.close()

    return redirect(
        url_for(
            "take_quiz",
            quiz_id=quiz_id
        )
    )


# ---------------------------------------------------------------------------
# 3. Quiz
# ---------------------------------------------------------------------------

@app.route("/quiz/<int:quiz_id>")
def take_quiz(quiz_id):

    db = get_db()

    quiz = db.execute(
        "SELECT * FROM quizzes WHERE id = ?",
        (quiz_id,)
    ).fetchone()

    db.close()

    if quiz is None:

        flash(
            "Quiz not found.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    questions = json.loads(
        quiz["questions_json"]
    )

    # Do not send correct answers to the browser.
    questions_for_client = [
        {
            "question": q["question"],
            "options": q["options"]
        }
        for q in questions
    ]

    return render_template(
        "quiz.html",
        quiz=quiz,
        questions_json=json.dumps(
            questions_for_client
        ),
        total_questions=len(questions),
    )


@app.route("/submit_quiz/<int:quiz_id>", methods=["POST"])
def submit_quiz(quiz_id):

    payload = request.get_json(
        silent=True
    ) or {}

    answers = payload.get(
        "answers",
        []
    )

    db = get_db()

    quiz = db.execute(
        "SELECT * FROM quizzes WHERE id = ?",
        (quiz_id,)
    ).fetchone()

    if quiz is None:

        db.close()

        return jsonify(
            {
                "error": "Quiz not found."
            }
        ), 404

    questions = json.loads(
        quiz["questions_json"]
    )

    total = len(questions)

    score = 0

    for i, q in enumerate(questions):

        selected = (
            answers[i]
            if i < len(answers)
            else None
        )

        if (
            isinstance(selected, int)
            and selected == q["correct_index"]
        ):
            score += 1

    percentage = (
        round(
            (score / total) * 100,
            1
        )
        if total > 0
        else 0.0
    )

    cursor = db.execute(
        "INSERT INTO attempts "
        "(quiz_id, topic, difficulty, score, total, percentage, answers_json, taken_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            quiz_id,
            quiz["topic"],
            quiz["difficulty"],
            score,
            total,
            percentage,
            json.dumps(answers),
            datetime.now().isoformat(),
        ),
    )

    db.commit()

    attempt_id = cursor.lastrowid

    db.close()

    record_study_session()

    return jsonify(
        {
            "attempt_id": attempt_id
        }
    )


# ---------------------------------------------------------------------------
# Result page
# ---------------------------------------------------------------------------

@app.route("/result/<int:attempt_id>")
def show_result(attempt_id):

    db = get_db()

    attempt = db.execute(
        "SELECT * FROM attempts WHERE id = ?",
        (attempt_id,)
    ).fetchone()

    if attempt is None:

        db.close()

        flash(
            "Result not found.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    quiz = db.execute(
        "SELECT * FROM quizzes WHERE id = ?",
        (attempt["quiz_id"],)
    ).fetchone()

    db.close()

    questions = json.loads(
        quiz["questions_json"]
    )

    student_answers = json.loads(
        attempt["answers_json"]
    )

    review = []

    for i, q in enumerate(questions):

        selected = (
            student_answers[i]
            if i < len(student_answers)
            else None
        )

        review.append(
            {
                "question": q["question"],
                "options": q["options"],
                "correct_index": q["correct_index"],
                "selected_index": selected,
                "is_correct": (
                    selected == q["correct_index"]
                ),
                "explanation": q.get(
                    "explanation",
                    ""
                ),
            }
        )

    streak = get_streak_info()

    return render_template(
        "result.html",
        attempt=attempt,
        review=review,
        streak=streak
    )


# ---------------------------------------------------------------------------
# Start application
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
