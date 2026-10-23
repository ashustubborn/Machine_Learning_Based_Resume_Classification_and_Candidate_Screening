# Screening Desk — AI Resume Screening System

A complete resume-screening project combining **NLP** (text cleaning, skill
extraction) and **classification** (TF-IDF + Logistic Regression), served
through a **Flask** web app.

## What it does

1. **Upload one or more resumes** (up to 25 at once; `.pdf`, `.docx`, `.txt`).
2. The app extracts and cleans the text (NLP preprocessing: lowercasing,
   URL/email/phone stripping, stopword removal).
3. A trained **TF-IDF + Logistic Regression** classifier predicts the most
   likely **job category** (10 categories) with a confidence score.
4. A skill-extraction module pulls out ~150 known technical/soft skills found
   in the resume.
5. *(Optional)* Paste a **job description** — the app computes a skill-match
   percentage, and lists matched vs. missing skills.

Everything runs locally. No external API calls, no internet dependency at
runtime.

## Project structure

```
resume_screener/
├── app.py                     # Flask web server
├── requirements.txt
├── data/
│   ├── generate_dataset.py    # synthetic training-data generator
│   └── resume_dataset.csv     # generated dataset (1,800 resumes, 10 categories)
├── model/
│   ├── train_model.py         # trains + saves the classifier
│   ├── tfidf_vectorizer.pkl   # trained TF-IDF vectorizer (generated)
│   └── classifier.pkl         # trained Logistic Regression model (generated)
├── utils/
│   ├── preprocess.py          # NLP cleaning pipeline
│   ├── skills.py              # skill extraction + JD matching
│   └── file_extract.py        # pdf/docx/txt text extraction
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── script.js
└── uploads/                   # temp storage, files are deleted right after reading
```

## How to run it on your machine (localhost)

**1. Requirements:** Python 3.9+.

**2. Install dependencies:**
```bash
cd resume_screener
pip install -r requirements.txt
```

**3. (Already done for you, but if you want to retrain):**
```bash
python data/generate_dataset.py   # regenerate the dataset
python model/train_model.py       # retrain and save the model
```
This prints a held-out accuracy/classification report and writes
`model/tfidf_vectorizer.pkl` and `model/classifier.pkl`. The trained
model files are already included in this download, so this step is optional.

**4. Start the web app:**
```bash
python app.py
```

**5. Open your browser at:**
```
http://127.0.0.1:5000
```

Upload a resume, optionally paste a job description, and click
**"Screen this resume."**

## The 10 trained job categories

Data Science · Python Developer · Java Developer · Web Developer · HR ·
Testing / QA · DevOps Engineer · Business Analyst · Sales ·
Mechanical Engineer

## Notes on the training data

Public resume datasets require downloads that aren't reachable in every
environment, so `data/generate_dataset.py` synthesizes realistic resumes from
large per-category skill/role/education pools. This keeps the project fully
self-contained and reproducible.

**To use your own real resume dataset instead:** replace
`data/resume_dataset.csv` with a CSV that has two columns, `Category` and
`Resume` (one row per resume, any number of categories), then re-run
`python model/train_model.py`. No other code changes are needed — the
Flask app automatically picks up the new `classifier.pkl`.

## Extending the project

- **Add more skills:** edit the `skills` lists inside
  `data/generate_dataset.py` (`CATEGORY_POOLS`) — `utils/skills.py` builds
  its master skill list from the same source.
- **Swap the classifier:** `model/train_model.py` is a single, short script —
  try `LinearSVC`, `RandomForestClassifier`, or a fine-tuned transformer in
  place of `LogisticRegression`.
- **Add authentication / a database of screened candidates:** `app.py` is a
  small, single-file Flask app — a natural place to add a `SQLAlchemy` model
  to persist screening results.


## Batch screening and history

- Upload several resumes at once (Ctrl/Shift-click in the file picker, or drag many files in).
- With a job description, candidates are ranked by skill-match %; without one, by classifier confidence.
- Every screening is saved automatically in a local SQLite file (`history.db`, created on first run).
- Open the **History** tab to re-open an old screening, delete one, or clear everything.
- To wipe history manually, delete `history.db` while the app is stopped.
