<<<<<<< HEAD
# fineprint. - AI Privacy & Consent Analyzer

Paste a website URL -> get a 0-100 privacy score, a plain-English summary, risky-clause detection,
tracker/cookie detection, permission analysis, a comparison and a downloadable report.

## Run it in VS Code
1. Open this folder in VS Code (File > Open Folder).
2. Terminal > New Terminal, then:
   ```
   python -m venv .venv
   .venv\Scripts\activate          # Windows      (Mac/Linux: source .venv/bin/activate)
   pip install -r requirements.txt
   python run.py
   ```
3. Open http://127.0.0.1:8000

The first registered account is the admin and sees the "System insights" panel.
API docs (auto-generated): http://127.0.0.1:8000/docs

## Structure
- backend/main.py       FastAPI routes + serves the frontend
- backend/analyzer.py   crawler, trackers, cookies, permissions, scoring
- backend/ml_model.py   NLP clause classifier (TF-IDF + Logistic Regression + rules)
- backend/training_data.py  add more example sentences here to improve accuracy
  (delete backend/model.pkl afterwards so it retrains)
- backend/database.py   SQLite: users, scans, analytics
- frontend/             index.html, style.css, app.js
=======
# fineprint-
My first project uploaded to GitHub
>>>>>>> eb0bbfb7bdf8b1137efceb71fdf6eb8f5ab5a9ab
