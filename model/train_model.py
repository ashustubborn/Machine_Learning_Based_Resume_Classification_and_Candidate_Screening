"""
Trains the resume-category classifier:
  raw resume text -> NLP cleaning -> TF-IDF vectorization -> Logistic Regression

Saves two artifacts:
  model/tfidf_vectorizer.pkl
  model/classifier.pkl
and prints a held-out classification report.
"""

import os
import sys
import pickle

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.preprocess import preprocess_for_model  # noqa: E402

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "resume_dataset.csv")
MODEL_DIR = os.path.join(BASE_DIR, "model")


def main():
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} resumes across {df['Category'].nunique()} categories")

    df["clean_text"] = df["Resume"].apply(preprocess_for_model)

    X_train, X_test, y_train, y_test = train_test_split(
        df["clean_text"], df["Category"], test_size=0.2, random_state=42, stratify=df["Category"]
    )

    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=2,
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    clf = LogisticRegression(max_iter=1000, C=5.0)
    clf.fit(X_train_vec, y_train)

    preds = clf.predict(X_test_vec)
    acc = accuracy_score(y_test, preds)
    print(f"\nHeld-out accuracy: {acc:.4f}\n")
    print(classification_report(y_test, preds))

    with open(os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"), "wb") as f:
        pickle.dump(vectorizer, f)
    with open(os.path.join(MODEL_DIR, "classifier.pkl"), "wb") as f:
        pickle.dump(clf, f)

    print(f"\nSaved vectorizer + classifier to {MODEL_DIR}")


if __name__ == "__main__":
    main()
