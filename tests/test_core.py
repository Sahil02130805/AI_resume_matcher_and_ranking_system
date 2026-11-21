import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(tempfile.mkdtemp(), "t.db"))
os.environ["USE_TFIDF"] = "1"          # deterministic, offline
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.nlp import extract_skills
from app.jd import analyze_jd
from app.parser import merged_months, parse_resume, parse_jobs
from evaluate import evaluate

SAMPLES = Path(__file__).resolve().parents[1] / "sample_data"
client = TestClient(app)


def test_skill_extraction_boundaries_and_aliases():
    s = extract_skills("REST APIs with Spring Boot, k8s, Postgres, JavaScript, NoSQL, Node.js, CI/CD; the rest of the team; spring 2019")
    assert {"REST APIs", "Spring Boot", "Kubernetes", "PostgreSQL", "JavaScript", "NoSQL", "Node.js", "CI/CD"} <= s
    assert not ({"Java", "SQL", "Spring"} & s)          # no substring leaks; ordinary words ignored


def test_overlapping_jobs_not_double_counted():
    assert merged_months([(2020 * 12 + 1, 2020 * 12 + 12), (2020 * 12 + 6, 2021 * 12 + 6)]) == 18


def test_job_parsing_title_on_previous_line():
    jobs = parse_jobs("Acme Corp\nBackend Engineer\nJan 2020 - Dec 2021\n- Built APIs in Java")
    assert jobs[0]["title"] and jobs[0]["months"] == 24 and "Java" in jobs[0]["skills"]


def test_jd_extraction():
    jd = analyze_jd((SAMPLES / "job_description.txt").read_text())
    assert "Java" in jd["required_skills"] and "Kafka" in jd["preferred_skills"]
    assert jd["min_experience_years"] == 4 and jd["education_level"] == 2
    assert next(r for r in jd["skill_requirements"] if r["label"] == "Java")["weight"] == 3.0     # title skill is core


def test_jd_alternatives_and_skill_years():
    jd = analyze_jd("Python Developer\nRequirements:\n- 3+ years of experience with Python and Kafka or RabbitMQ\n- 5-8 years of overall experience\nPreferred:\n- AWS")
    labels = {r["label"]: r for r in jd["skill_requirements"]}
    assert "Kafka / RabbitMQ" in labels and labels["Python"]["min_years"] == 3
    assert labels["AWS"]["kind"] == "preferred" and (jd["min_experience_years"], jd["max_experience_years"]) == (5.0, 8.0)


def test_resume_parsing_pdf_and_docx():
    files = sorted((SAMPLES / "resumes").iterdir())
    assert {p.suffix for p in files} == {".pdf", ".docx"}
    for p in files:
        r = parse_resume(p.name, p.read_bytes())
        assert r["email"] and r["name"] and r["skills"] and r["total_experience_years"] > 0 and r["jobs"]


def test_ranking_quality_against_gold_labels():
    ndcg, acc, res = evaluate(verbose=False)
    assert ndcg >= 0.95 and acc >= 0.9
    byname = {r["name"]: r for r in res}
    assert byname["Rahul Bansal"]["score"] <= 35.5 and "capped" in " ".join(byname["Rahul Bansal"]["reasons"])   # keyword stuffer
    isha = byname["Isha Rao"]                                                                                    # overlapping jobs
    assert 7.2 <= isha["experience"]["candidate_total"] <= 7.6   # union of dates; double counting the freelance overlap would give ~8.9


def test_related_skill_and_evidence_credit():
    c = {x["name"]: x for x in client.post("/api/analyze-sample").json()["candidates"]}
    spring = next(m for m in c["Rohan Kulkarni"]["matched_skills"] if m["skill"] == "Spring Boot")
    assert spring["type"] == "related" and 0 < spring["credit"] < 1
    docker = next(m for m in c["Meera Reddy"]["matched_skills"] if m["skill"] == "Docker")
    assert docker["evidence"] == "listed" and docker["credit"] == 0.75


def test_api_persistence_and_detail():
    r = client.post("/api/analyze-sample").json()
    assert len(r["candidates"]) == 14 and all(0 <= x["score"] <= 100 for x in r["candidates"])
    d = client.get(f"/api/analyses/{r['id']}/candidates/c1").json()
    assert d["candidate"]["reasons"] and d["candidate"]["breakdown"]
    assert client.get(f"/api/analyses/{r['id']}").json()["candidates"][0]["rank"] == 1


def test_batch_upload_endpoint_and_duplicates():
    files = [("resumes", (p.name, p.read_bytes(), "application/octet-stream")) for p in sorted((SAMPLES / "resumes").iterdir())]
    dup = files[0]
    files.append(("resumes", ("copy_" + dup[1][0], dup[1][1], "application/pdf")))
    r = client.post("/api/analyze", data={"jd_text": (SAMPLES / "job_description.txt").read_text()}, files=files)
    assert r.status_code == 200 and len(r.json()["candidates"]) == 14
    assert any("Duplicate" in e["error"] for e in r.json()["errors"])


def test_bad_inputs():
    assert client.post("/api/jd/parse", data={"jd_text": ""}).status_code == 400
    files = [("resumes", ("x.pdf", b"not a pdf", "application/pdf"))]
    assert client.post("/api/analyze", data={"jd_text": "Java developer, 2 years experience"}, files=files).status_code == 400
