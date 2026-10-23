"""
Generates a synthetic but realistic resume dataset for training the
classification model. Each row = one resume's raw text + its job category.

Why synthetic? Public resume datasets (e.g. Kaggle) require downloads from
domains not reachable in this environment, so we build a template-based
generator with large keyword pools per category. This produces enough
lexical signal for TF-IDF + Logistic Regression to learn clean decision
boundaries, and is easy to extend with your own real resumes later
(just append rows with the same two columns: Category, Resume).
"""

import csv
import random

random.seed(42)

# ---------------------------------------------------------------------------
# Category -> pools of skills / tools / phrases used to synthesize resumes
# ---------------------------------------------------------------------------
CATEGORY_POOLS = {
    "Data Science": {
        "skills": ["python", "pandas", "numpy", "scikit-learn", "tensorflow", "keras",
                   "pytorch", "machine learning", "deep learning", "data visualization",
                   "matplotlib", "seaborn", "sql", "statistics", "regression",
                   "classification", "clustering", "nlp", "computer vision", "xgboost",
                   "feature engineering", "data cleaning", "jupyter", "tableau", "power bi",
                   "hypothesis testing", "a/b testing", "big data", "spark", "hadoop"],
        "roles": ["Data Scientist", "Machine Learning Engineer", "Data Analyst",
                  "AI Researcher", "Applied Scientist"],
        "edu": ["B.Tech in Computer Science", "M.Sc in Statistics", "M.Tech in Data Science",
                "B.E in Information Technology", "MSc in Applied Mathematics"],
    },
    "Python Developer": {
        "skills": ["python", "django", "flask", "fastapi", "rest api", "postgresql",
                   "mysql", "celery", "redis", "docker", "unit testing", "pytest",
                   "object oriented programming", "microservices", "git", "linux",
                   "asyncio", "sqlalchemy", "graphql", "aws lambda", "ci/cd"],
        "roles": ["Python Developer", "Backend Developer", "Software Engineer",
                  "API Developer"],
        "edu": ["B.Tech in Computer Science", "B.E in Information Technology",
                "BCA", "MCA"],
    },
    "Java Developer": {
        "skills": ["java", "spring boot", "spring mvc", "hibernate", "microservices",
                   "rest api", "maven", "gradle", "junit", "kafka", "multithreading",
                   "design patterns", "sql", "oracle database", "docker", "kubernetes",
                   "jenkins", "git", "aws", "collections framework"],
        "roles": ["Java Developer", "Backend Engineer", "Software Engineer",
                  "Java Full Stack Developer"],
        "edu": ["B.Tech in Computer Science", "B.E in Electronics", "MCA",
                "M.Tech in Software Engineering"],
    },
    "Web Developer": {
        "skills": ["html", "css", "javascript", "react", "angular", "vue.js", "node.js",
                   "express.js", "mongodb", "redux", "typescript", "webpack", "sass",
                   "bootstrap", "tailwind css", "rest api", "responsive design",
                   "next.js", "graphql", "git", "web accessibility"],
        "roles": ["Web Developer", "Frontend Developer", "Full Stack Developer",
                  "UI Developer"],
        "edu": ["B.Tech in Computer Science", "BCA", "B.Sc in Computer Science",
                "Diploma in Web Design"],
    },
    "HR": {
        "skills": ["recruitment", "talent acquisition", "onboarding", "employee relations",
                   "performance management", "payroll", "hr policies", "compensation and benefits",
                   "hris", "workday", "sap successfactors", "conflict resolution",
                   "training and development", "labour law", "exit interviews",
                   "employer branding", "diversity and inclusion", "succession planning"],
        "roles": ["HR Executive", "HR Business Partner", "Talent Acquisition Specialist",
                  "HR Manager", "People Operations Specialist"],
        "edu": ["MBA in Human Resources", "PGDM in HR", "BBA", "MA in Psychology",
                "Post Graduate Diploma in Personnel Management"],
    },
    "Testing / QA": {
        "skills": ["manual testing", "automation testing", "selenium", "test cases",
                   "regression testing", "bug tracking", "jira", "postman", "api testing",
                   "load testing", "jmeter", "cypress", "test plans", "sql", "agile",
                   "test automation framework", "sdlc", "stlc", "defect life cycle"],
        "roles": ["QA Engineer", "Software Tester", "Test Automation Engineer",
                  "QA Analyst", "SDET"],
        "edu": ["B.Tech in Computer Science", "B.E in Information Technology",
                "BCA", "B.Sc in Computer Science"],
    },
    "DevOps Engineer": {
        "skills": ["aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
                   "jenkins", "ci/cd pipelines", "linux administration", "bash scripting",
                   "monitoring", "prometheus", "grafana", "git", "cloudformation",
                   "infrastructure as code", "helm", "networking", "load balancing"],
        "roles": ["DevOps Engineer", "Site Reliability Engineer", "Cloud Engineer",
                  "Infrastructure Engineer"],
        "edu": ["B.Tech in Computer Science", "B.E in Electronics and Communication",
                "M.Tech in Cloud Computing"],
    },
    "Business Analyst": {
        "skills": ["requirement gathering", "business process modeling", "sql",
                   "stakeholder management", "data analysis", "excel", "power bi",
                   "tableau", "user stories", "agile", "scrum", "gap analysis",
                   "documentation", "uml diagrams", "process improvement",
                   "financial modeling", "market research"],
        "roles": ["Business Analyst", "Product Analyst", "Systems Analyst",
                  "Functional Consultant"],
        "edu": ["MBA in Finance", "B.Tech with MBA", "BBA", "M.Com",
                "PGDM in Business Analytics"],
    },
    "Sales": {
        "skills": ["lead generation", "client relationship management", "crm software",
                   "salesforce", "negotiation", "cold calling", "b2b sales", "b2c sales",
                   "target achievement", "sales forecasting", "account management",
                   "customer retention", "presentation skills", "market analysis",
                   "revenue growth", "upselling"],
        "roles": ["Sales Executive", "Business Development Manager", "Account Manager",
                  "Sales Representative", "Regional Sales Manager"],
        "edu": ["MBA in Marketing", "BBA", "B.Com", "PGDM in Sales and Marketing"],
    },
    "Mechanical Engineer": {
        "skills": ["autocad", "solidworks", "catia", "ansys", "product design",
                   "manufacturing processes", "quality control", "gd&t", "cnc machining",
                   "thermodynamics", "hvac systems", "project management", "six sigma",
                   "lean manufacturing", "material science", "cad modeling"],
        "roles": ["Mechanical Engineer", "Design Engineer", "Production Engineer",
                  "Quality Engineer", "Manufacturing Engineer"],
        "edu": ["B.Tech in Mechanical Engineering", "B.E in Mechanical Engineering",
                "M.Tech in Mechanical Engineering", "Diploma in Mechanical Engineering"],
    },
}

SUMMARY_TEMPLATES = [
    "Result-driven {role} with {years} years of experience in {skill_a}, {skill_b} and {skill_c}. "
    "Proven track record of delivering high-quality outcomes in fast-paced environments.",
    "{role} with {years} years of hands-on experience specializing in {skill_a} and {skill_b}. "
    "Strong problem-solving ability and passion for {skill_c}.",
    "Motivated {role} having {years} years of professional experience across {skill_a}, "
    "{skill_b} and {skill_c}. Adept at collaborating with cross-functional teams.",
    "Detail-oriented {role} with expertise in {skill_a}, {skill_b} and {skill_c}, "
    "backed by {years} years of industry experience.",
]

PROJECT_TEMPLATES = [
    "Led a project involving {skill_a} and {skill_b} that improved efficiency significantly.",
    "Built and deployed a solution using {skill_a}, {skill_b} and {skill_c} for a client engagement.",
    "Worked extensively with {skill_a} and {skill_c} to streamline internal processes.",
    "Collaborated with a team of engineers on a {skill_a} based initiative, also utilizing {skill_b}.",
]

CERT_POOL = ["Certified {s} Professional", "{s} Certification", "Advanced {s} Workshop"]


def make_resume(category):
    pool = CATEGORY_POOLS[category]
    skills = random.sample(pool["skills"], k=min(8, len(pool["skills"])))
    role = random.choice(pool["roles"])
    edu = random.choice(pool["edu"])
    years = random.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

    s = random.sample(skills, 3)
    summary = random.choice(SUMMARY_TEMPLATES).format(
        role=role, years=years, skill_a=s[0], skill_b=s[1], skill_c=s[2]
    )

    proj_s = random.sample(skills, 3)
    project = random.choice(PROJECT_TEMPLATES).format(
        skill_a=proj_s[0], skill_b=proj_s[1], skill_c=proj_s[2]
    )

    cert_skill = random.choice(skills)
    cert = random.choice(CERT_POOL).format(s=cert_skill.title())

    skills_line = "Skills: " + ", ".join(skills) + "."
    edu_line = f"Education: {edu}."
    exp_line = f"Experience: {years} years as {role}."
    cert_line = f"Certifications: {cert}."

    resume_text = " ".join([summary, skills_line, exp_line, project, edu_line, cert_line])
    return resume_text


def build_dataset(samples_per_category=180):
    rows = []
    for category in CATEGORY_POOLS:
        for _ in range(samples_per_category):
            rows.append((category, make_resume(category)))
    random.shuffle(rows)
    return rows


if __name__ == "__main__":
    rows = build_dataset()
    out_path = "/home/claude/resume_screener/data/resume_dataset.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Category", "Resume"])
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out_path}")
    print("Categories:", list(CATEGORY_POOLS.keys()))
