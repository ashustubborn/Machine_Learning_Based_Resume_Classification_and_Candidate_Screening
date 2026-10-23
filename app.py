import os
import pickle

from flask import Flask, render_template, request, jsonify

from utils.preprocess import preprocess_for_model
from utils.skills import extract_skills, match_resume_to_job
from utils.file_extract import extract_text_from_storage
from utils import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "model")
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
MAX_FILES_PER_BATCH = 25

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 40 * 1024 * 1024  # 40 MB total per batch

db.init_db()


def load_model():
    with open(os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"), "rb") as f:
        vectorizer = pickle.load(f)
    with open(os.path.join(MODEL_DIR, "classifier.pkl"), "rb") as f:
        classifier = pickle.load(f)
    return vectorizer, classifier


try:
    VECTORIZER, CLASSIFIER = load_model()
except Exception as e:
    # Model files missing or saved with an incompatible scikit-learn version -> retrain automatically.
    print(f"Could not load saved model ({e}). Retraining...")
    from model.train_model import main as train_main
    train_main()
    VECTORIZER, CLASSIFIER = load_model()

CLASS_LABELS = list(CLASSIFIER.classes_)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def classify_resume(raw_text: str):
    cleaned = preprocess_for_model(raw_text)
    vec = VECTORIZER.transform([cleaned])
    probs = CLASSIFIER.predict_proba(vec)[0]
    ranked = sorted(zip(CLASS_LABELS, probs), key=lambda x: x[1], reverse=True)
    top_category, top_prob = ranked[0]
    top5 = [{"category": c, "confidence": round(float(p) * 100, 1)} for c, p in ranked[:5]]
    return top_category, round(float(top_prob) * 100, 1), top5


def process_one_resume(file_storage, job_description: str):
    """Runs the full pipeline on one uploaded file. Returns a result dict."""
    filename = file_storage.filename

    if not allowed_file(filename):
        return {"filename": filename, "error": "Unsupported file type. Use .pdf, .docx, or .txt"}

    try:
        raw_text = extract_text_from_storage(file_storage)
    except Exception as e:
        return {"filename": filename, "error": f"Could not read file: {e}"}

    if not raw_text or not raw_text.strip():
        return {"filename": filename, "error": "No readable text found in this file."}

    top_category, top_confidence, top5 = classify_resume(raw_text)
    found_skills = extract_skills(raw_text)

    match_result = None
    if job_description:
        match_result = match_resume_to_job(raw_text, job_description)

    return {
        "filename": filename,
        "predicted_category": top_category,
        "confidence": top_confidence,
        "top5": top5,
        "skills_found": found_skills,
        "word_count": len(raw_text.split()),
        "match": match_result,
        "resume_preview": raw_text.strip()[:800],
    }


@app.route("/")
def index():
    return render_template("index.html", categories=sorted(CLASS_LABELS))


@app.route("/analyze", methods=["POST"])
def analyze():
    files = [f for f in request.files.getlist("resumes") if f and f.filename]

    if not files:
        return jsonify({"error": "Please upload at least one resume file (.pdf, .docx, or .txt)."}), 400

    if len(files) > MAX_FILES_PER_BATCH:
        return jsonify({"error": f"Please upload at most {MAX_FILES_PER_BATCH} resumes at once."}), 400

    job_description = request.form.get("job_description", "").strip()

    results = [process_one_resume(f, job_description) for f in files]
    ok_results = [r for r in results if "error" not in r]
    failed_results = [r for r in results if "error" in r]

    # Rank by job-description match % when available, otherwise by classifier confidence.
    if job_description:
        ok_results.sort(
            key=lambda r: (r["match"]["match_percent"]
                           if r["match"] and r["match"]["match_percent"] is not None else -1),
            reverse=True,
        )
    else:
        ok_results.sort(key=lambda r: r["confidence"], reverse=True)

    for i, r in enumerate(ok_results, start=1):
        r["rank"] = i

    ranked_by = "match" if job_description else "confidence"

    screening_id, created_at = None, None
    if ok_results:  # only save screenings that produced at least one result
        screening_id, created_at = db.save_screening(
            job_description, ranked_by, ok_results, failed_results, len(files)
        )

    return jsonify({
        "screening_id": screening_id,
        "created_at": created_at,
        "job_description": job_description,
        "batch_mode": len(files) > 1,
        "ranked_by": ranked_by,
        "results": ok_results,
        "failed": failed_results,
        "total_uploaded": len(files),
    })


# ---------------------------------------------------------------------------
# History endpoints
# ---------------------------------------------------------------------------
@app.route("/history", methods=["GET"])
def history_list():
    return jsonify({"items": db.list_screenings()})


@app.route("/history/<int:screening_id>", methods=["GET"])
def history_detail(screening_id):
    data = db.get_screening(screening_id)
    if data is None:
        return jsonify({"error": "Screening not found."}), 404
    return jsonify(data)


@app.route("/history/<int:screening_id>", methods=["DELETE"])
def history_delete(screening_id):
    if not db.delete_screening(screening_id):
        return jsonify({"error": "Screening not found."}), 404
    return jsonify({"deleted": screening_id})


@app.route("/history", methods=["DELETE"])
def history_clear():
    db.clear_all()
    return jsonify({"cleared": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
