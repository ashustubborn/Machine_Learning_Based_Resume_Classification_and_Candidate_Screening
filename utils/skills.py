"""
Skill extraction + resume-vs-job-description matching.
Uses a curated master skill list (union of all category skill pools) and
simple phrase matching on cleaned text — robust to word order and works
without any external NLP model download.
"""

import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.generate_dataset import CATEGORY_POOLS  # noqa: E402
from utils.preprocess import clean_text  # noqa: E402

# Master skill list = union of every category's skill pool, deduplicated,
# longest phrases first so multi-word skills match before their substrings
# (e.g. "machine learning" before "learning").
_ALL_SKILLS = sorted(
    {s for pool in CATEGORY_POOLS.values() for s in pool["skills"]},
    key=len,
    reverse=True,
)


def extract_skills(text: str):
    """Return the sorted list of known skills found in the given raw text."""
    cleaned = clean_text(text)
    found = set()
    remaining = cleaned
    for skill in _ALL_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, remaining):
            found.add(skill)
    return sorted(found)


def match_resume_to_job(resume_text: str, job_description: str):
    """
    Compares extracted skills between a resume and a job description.
    Returns match percentage plus matched / missing skill lists.
    """
    resume_skills = set(extract_skills(resume_text))
    jd_skills = set(extract_skills(job_description))

    if not jd_skills:
        return {
            "match_percent": None,
            "matched_skills": sorted(resume_skills),
            "missing_skills": [],
            "jd_skills": [],
        }

    matched = resume_skills & jd_skills
    missing = jd_skills - resume_skills
    match_percent = round(100 * len(matched) / len(jd_skills), 1)

    return {
        "match_percent": match_percent,
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "jd_skills": sorted(jd_skills),
    }
