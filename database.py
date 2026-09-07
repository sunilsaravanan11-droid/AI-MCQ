"""
database.py
Handles the SQLite database connection and schema for the AI MCQ Generator.

Tables:
  documents  - each uploaded PDF, its extracted text, and detected topics
  quizzes    - a generated set of MCQs for a topic (correct answers live here)
  attempts   - a completed quiz attempt with score + student answers
  streak     - a single row (id=1) tracking the study streak
"""

import sqlite3
import os

DB_PATH = os.path.join("/tmp", "app.db")


def get_db():
    """Open a new database connection with rows returned as dict-like objects."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they do not already exist. Safe to call every startup."""
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            full_text TEXT NOT NULL,
            topics TEXT NOT NULL,          -- JSON list of topic names
            uploaded_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            num_questions INTEGER NOT NULL,
            questions_json TEXT NOT NULL,  -- list of {question, options[4], correct_index, explanation}
            created_at TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents (id)
        );

        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            percentage REAL NOT NULL,
            answers_json TEXT NOT NULL,    -- list of selected option indices (or null)
            taken_at TEXT NOT NULL,
            FOREIGN KEY (quiz_id) REFERENCES quizzes (id)
        );

        CREATE TABLE IF NOT EXISTS streak (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            current_streak INTEGER NOT NULL DEFAULT 0,
            longest_streak INTEGER NOT NULL DEFAULT 0,
            last_study_date TEXT
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()
