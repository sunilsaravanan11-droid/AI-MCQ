# AI MCQ Generator 🔥

A simple, beginner-friendly web app for students: upload a study PDF, pick a
topic, generate multiple-choice questions with AI, take the quiz, get your
score, and keep a daily study streak going.

**Flow:** Upload PDF → Select Topic → Generate MCQs → Take Quiz → Get Score → Maintain Streak 🔥

## Tech stack

- **Frontend:** HTML, CSS, JavaScript (server-rendered with Jinja templates)
- **Backend:** Python Flask
- **Database:** SQLite (file-based, zero setup)
- **PDF parsing:** PyMuPDF
- **AI:** Groq API (free & fast, default) or OpenAI API — both used via plain HTTP calls

## Project structure

```
ai_mcq_generator/
├── app.py                  # Flask routes (the whole app flow lives here)
├── database.py              # SQLite schema + connection helper
├── services/
│   ├── pdf_service.py       # PDF text extraction + topic-relevant excerpting
│   ├── ai_service.py        # Calls the AI to detect topics & generate MCQs
│   └── streak_service.py    # Daily streak logic
├── templates/                # Jinja HTML pages
│   ├── base.html
│   ├── index.html            # Dashboard
│   ├── topics.html           # Topic + quiz settings
│   ├── quiz.html              # One-question-at-a-time quiz
│   └── result.html            # Score + answer review
├── static/
│   ├── css/style.css
│   └── js/app.js
├── uploads/                  # Uploaded PDFs are stored here
├── data/                     # app.db (SQLite) is created here
├── requirements.txt
└── .env.example
```

## Setup

1. **Install dependencies** (Python 3.9+ recommended):

   ```bash
   cd ai_mcq_generator
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Get a free AI API key.**  The app defaults to **Groq** (fast, free tier,
   no credit card needed):

   - Go to https://console.groq.com/keys and create a key.
   - (Alternatively, use OpenAI: get a key from https://platform.openai.com/api-keys)

3. **Configure environment variables:**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and paste your key:

   ```
   AI_PROVIDER=groq
   GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
   ```

4. **Run the app:**

   ```bash
   python app.py
   ```

   Open **http://localhost:5000** in your browser.

## How it works

1. **Upload PDF** — The PDF is parsed with PyMuPDF to plain text. The text
   is sent to the AI, which returns a short list of topics actually present
   in the document.
2. **Select Topic** — Pick one detected topic, how many questions (5/10/15/20),
   and a difficulty (Easy/Medium/Hard).
3. **Generate MCQs** — The app pulls the paragraphs most relevant to that
   topic out of the PDF text and asks the AI to write MCQs **strictly from
   that material** — 4 options, exactly one correct answer, plus a short
   explanation. The correct answers are stored server-side only.
4. **Take Quiz** — Questions are shown one at a time with a progress bar.
   The correct answers are never sent to the browser until you submit.
5. **Get Score** — The server grades your answers, shows your score,
   percentage, and a full review (your answer vs. the correct one, with
   an explanation for each question).
6. **Study Streak 🔥** — Completing at least one quiz today counts as a
   study day. Multiple quizzes the same day still count once. Missing a
   day resets the streak to 1 the next time you study. The dashboard shows
   your current streak, longest streak, and last study date.

## Notes

- The database (`data/app.db`) and uploaded files (`uploads/`) are created
  automatically on first run.
- Local accounts are stored in SQLite with hashed passwords. Set the default
   account values in `.env` before first use.
- If a PDF is very large, the app focuses AI calls on the most relevant
  excerpt for the chosen topic to keep generation fast and on-topic.
