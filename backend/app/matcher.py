"""Hybrid, explainable resume <-> JD scoring.

  score = min( ceiling , 100 * sum_i w_i * component_i )      (weights re-normalised if a component is N/A)

  Skills      45%  per requirement: 1.0 direct | partial for related/embedding-similar skills, then multiplied by
                   evidence (used in a job 1.0 / project 0.9 / only listed 0.75), years-vs-required, recency.
                   Weights: title skill 3.0, required 1.0, preferred 0.5. "A or B" requirements: best member wins.
  Semantic    25%  every JD requirement sentence vs. its best-matching resume sentence (embedding cosine).
  Experience  20%  (0.7 * relevant_years + 0.3 * total_years) / required_years, capped at 1.
                   relevant_years weights each job month by how much of the JD that job covers.
  Education   10%  meets level 1.0, one level below 0.6, lower 0.3.
  Ceilings         a candidate covering few required skills cannot be rescued by soft semantic similarity, and a
                   keyword-stuffed resume cannot score high without work evidence:
                   ceiling = 35 + 65 * min(1, coverage/0.7)  and  35 + 65 * min(1, evidenced_coverage/0.5).
"""
import numpy as np
from .parser import NOW_IDX, LEVEL_NAMES, weighted_years
from .skills import RELATED
from .nlp import sentences

WEIGHTS = {"skills": 0.45, "semantic": 0.25, "experience": 0.20, "education": 0.10}
SEM_SKILL_MIN = 0.55            # cosine needed for embedding-based skill credit (transformer backend only)
EVID = {"job": 1.0, "project": 0.9, "listed": 0.75}


def _fmt(idx):
    return f"{(idx - 1) // 12}-{(idx - 1) % 12 + 1:02d}"


PRACTICES = {"Agile", "Git"}   # rarely appear in bullets, so "listed only" is not penalised


def _factors(info, has_jobs, skill=None):
    """evidence x recency multiplier for a resume skill + human-readable notes."""
    if not has_jobs:
        return 1.0, "stated", []
    notes, f = [], 1.0
    if info["jobs"]:
        kind = "job"
        gap = NOW_IDX - info["last_end"]
        rec = 1.0 if gap <= 36 else 0.9 if gap <= 72 else 0.8
        if rec < 1:
            notes.append(f"last used {_fmt(info['last_end'])} (×{rec})")
        f *= rec
    elif info["projects"]:
        kind = "project"
        notes.append("only shown in projects (×0.9)")
    elif skill in PRACTICES:
        return f, "listed", notes
    else:
        kind = "listed"
        notes.append("listed but never shown in a job (×0.75)")
    return f * EVID[kind], kind, notes


def _req_credit(req, ctx):
    resume, enc, have_vecs, has_jobs = ctx["resume"], ctx["enc"], ctx["have_vecs"], ctx["has_jobs"]
    idx, best = resume["skill_index"], None
    for m in req["members"]:
        cands = []
        if m in idx:
            f, ev, notes = _factors(idx[m], has_jobs, m)
            yrs = round(idx[m]["months"] / 12, 1)
            if req["min_years"] and has_jobs:
                yf = 0.5 + 0.5 * min(1.0, yrs / req["min_years"])
                if yf < 1:
                    notes.append(f"{yrs:g} of {req['min_years']}+ yrs required (×{yf:.2f})")
                f *= yf
            cands.append((f, "exact", m, ev, yrs, notes))
        for h, c in RELATED.get(m, {}).items():
            if h in idx:
                f, ev, notes = _factors(idx[h], has_jobs, h)
                cands.append((c * f, "related", h, ev, round(idx[h]["months"] / 12, 1), notes))
        if enc.kind != "tfidf" and have_vecs is not None and m not in idx:
            sims = (enc.encode([m]) @ have_vecs.T)[0]
            i = int(np.argmax(sims))
            if sims[i] >= SEM_SKILL_MIN:
                h = ctx["have"][i]
                f, ev, notes = _factors(idx[h], has_jobs, h)
                cands.append((0.8 * float(sims[i]) * f, "semantic", h, ev, round(idx[h]["months"] / 12, 1), notes))
        for c in cands:
            if best is None or c[0] > best[0][0]:
                best = (c, m)
    if best is None:
        return {"credit": 0.0, "type": "missing"}
    (credit, kind, via, ev, yrs, notes), member = best
    return {"credit": round(credit, 3), "type": kind, "matched_with": via, "member": member,
            "evidence": ev, "years": yrs, "notes": notes,
            "last_used": _fmt(idx[via]["last_end"]) if idx[via]["last_end"] else None}


def match(jd, resume, enc, jd_vecs):
    has_jobs = bool(resume["jobs"])
    have = sorted(resume["skills"])
    have_vecs = enc.encode(have) if (enc.kind != "tfidf" and have) else None
    ctx = {"resume": resume, "enc": enc, "have_vecs": have_vecs, "have": have, "has_jobs": has_jobs}
    reqs = jd["skill_requirements"]

    # ---- 1. skills ----
    matched, missing, results = [], [], {}
    earned = possible = req_earned = req_possible = 0.0
    for r in reqs:
        c = _req_credit(r, ctx)
        results[r["id"]] = c
        possible += r["weight"]; earned += r["weight"] * c["credit"]
        if r["kind"] == "required":
            req_possible += r["weight"]; req_earned += r["weight"] * c["credit"]
        if c["credit"] <= 0:
            missing.append({"skill": r["label"], "required": r["kind"] == "required", "weight": r["weight"]})
        else:
            matched.append({"skill": r["label"], "required": r["kind"] == "required", "weight": r["weight"],
                            **{k: v for k, v in c.items() if k != "member"}})
    skills_score = earned / possible if possible else None
    coverage = req_earned / req_possible if req_possible else 1.0
    # share of required weight backed by actual work/project evidence (anti keyword-stuffing)
    ev_w = sum(m["weight"] for m in matched if m["required"] and m.get("evidence") in ("job", "project"))
    ev_coverage = (ev_w / req_possible) if (req_possible and has_jobs) else 1.0

    # ---- 2. semantic fit (+ evidence sentences) ----
    chunks = [s for key in ("summary", "experience", "projects") for s in sentences(resume["sections"].get(key, ""))] \
        or sentences(resume["text"])
    ev_list, raw, semantic = [], 0.0, 0.0
    if len(jd_vecs) and chunks:
        sims = jd_vecs @ enc.encode(chunks).T
        best_i, best_s = sims.argmax(axis=1), sims.max(axis=1)
        raw = float(best_s.mean())
        semantic = enc.calibrate(raw)
        for q, i, s in zip(jd["requirement_lines"], best_i, best_s):
            ev_list.append({"requirement": q, "resume_text": chunks[int(i)], "similarity": round(enc.calibrate(float(s)), 2)})
        ev_list.sort(key=lambda e: -e["similarity"])

    # ---- 3. experience (per-job relevance = share of JD requirements the job demonstrates) ----
    jobs = resume["jobs"]
    n_req = max(1, len([r for r in reqs if r["kind"] == "required"]))
    for j in jobs:
        js = set(j["skills"])
        got = 0.0
        for r in reqs:
            if r["kind"] != "required":
                continue
            if js & set(r["members"]):
                got += 1
            else:
                got += max((RELATED.get(m, {}).get(h, 0) for m in r["members"] for h in js), default=0) * 0.8
        j["relevance"] = round(min(1.0, (got / n_req) / 0.4), 2)   # covering 40% of requirements = fully relevant
        j["relevant"] = j["relevance"] >= 0.5
        j["matched_skills"] = sorted(js & {m for r in reqs for m in r["members"]})
    total = resume["total_experience_years"]
    relevant = min(weighted_years(jobs, key=lambda j: j["relevance"]), total) if jobs else total
    need, need_max = jd["min_experience_years"], jd.get("max_experience_years")
    exp_score = min(1.0, (0.7 * relevant + 0.3 * total) / need) if need else None

    # ---- 4. education ----
    edu_score = None
    if jd["education_level"]:
        gap = jd["education_level"] - resume["education_level"]
        edu_score = 1.0 if gap <= 0 else 0.6 if gap == 1 else 0.3

    comps = {"skills": skills_score, "semantic": semantic, "experience": exp_score, "education": edu_score}
    active = {k: v for k, v in comps.items() if v is not None}
    wsum = sum(WEIGHTS[k] for k in active)
    breakdown = {k: {"score": round(v * 100, 1), "weight": round(WEIGHTS[k] / wsum, 3),
                     "points": round(100 * WEIGHTS[k] / wsum * v, 1)} for k, v in active.items()}
    raw_score = sum(b["points"] for b in breakdown.values())
    ceiling = min(35 + 65 * min(1.0, coverage / 0.7), 35 + 65 * min(1.0, ev_coverage / 0.5))
    score = round(min(raw_score, ceiling), 1)

    # ---- explanation ----
    reasons = []
    req_m = [m for m in matched if m["required"]]
    n_req_all = len([r for r in reqs if r["kind"] == "required"])
    if n_req_all:
        direct = [m["skill"] for m in req_m if m["type"] == "exact" and m["credit"] >= 0.95]
        reasons.append(f"Covers {len(req_m)} of {n_req_all} required skills"
                       + (f"; fully evidenced: {', '.join(direct)}." if direct else "."))
    for m in matched:
        if m["type"] != "exact":
            reasons.append(f"{m['skill']}: not stated, but related skill {m['matched_with']} gives {int(m['credit']*100)}% credit.")
        elif m["credit"] < 0.95 and m["notes"]:
            reasons.append(f"{m['skill']}: {int(m['credit']*100)}% credit — " + "; ".join(m["notes"]) + ".")
    miss_req = [m["skill"] for m in missing if m["required"]]
    if miss_req:
        reasons.append(f"Missing required: {', '.join(miss_req)}.")
    if need:
        yrs_txt = f"{need:g}" + (f"–{need_max:g}" if need_max else "+")
        reasons.append((f"{relevant:g} yrs of JD-relevant experience meets the {yrs_txt} yrs requirement"
                        if relevant >= need else
                        f"Only {relevant:g} yrs JD-relevant experience ({total:g} total) vs {yrs_txt} required") + ".")
        if total - relevant >= 2:
            reasons.append(f"{total - relevant:.1f} yrs of the {total:g} total came from roles unrelated to this JD.")
    if jd["education_level"]:
        reasons.append(("Education meets" if edu_score == 1 else "Education is below") +
                       f" the {jd['education_label']} requirement ({LEVEL_NAMES[resume['education_level']]} found).")
    lvl = "strong" if semantic >= .7 else "moderate" if semantic >= .4 else "weak"
    reasons.append(f"Resume text vs JD responsibilities: {lvl} semantic alignment ({round(semantic*100)}%).")
    if score < raw_score - 0.05:
        why = (f"only {ev_coverage*100:.0f}% of required skills are backed by work/project evidence (keyword listing alone is not enough)"
               if ev_coverage < coverage else f"only {coverage*100:.0f}% of weighted required skills are covered")
        reasons.append(f"Score capped at {ceiling:.0f}: {why}.")

    return {
        "name": resume["name"], "email": resume["email"], "phone": resume["phone"], "filename": resume["filename"],
        "current_title": resume["current_title"], "score": score, "raw_score": round(raw_score, 1),
        "required_coverage": round(coverage, 3), "evidenced_coverage": round(ev_coverage, 3), "breakdown": breakdown,
        "matched_skills": matched, "missing_skills": missing,
        "extra_skills": sorted(set(have) - {m for r in reqs for m in r["members"]}), "all_skills": have,
        "experience": {"candidate_total": total, "candidate_relevant": round(relevant, 1), "required": need,
                       "required_max": need_max,
                       "verdict": None if not need else ("meets" if relevant >= need else "below")},
        "education": [{k: e[k] for k in ("degree", "field", "institution", "year", "text")} for e in resume["education"]],
        "summary": resume["summary"],
        "jobs": [{k: v for k, v in j.items() if k not in ("start_idx", "end_idx", "text")} for j in jobs],
        "evidence": {"strong": ev_list[:3], "weak": [e for e in ev_list[::-1] if e["similarity"] < 0.3][:3]},
        "reasons": reasons, "warnings": resume["warnings"], "parse_quality": resume["parse_quality"],
        "similarity_backend": enc.kind, "raw_similarity": round(raw, 3),
    }


def rank(jd, resumes):
    from .embeddings import Encoder
    corpus = [jd["text"]] + [r["text"] for r in resumes] + [s for r in resumes for s in sentences(r["text"])]
    enc = Encoder(corpus)
    jd_vecs = enc.encode(jd["requirement_lines"])
    results = [match(jd, r, enc, jd_vecs) for r in resumes]
    results.sort(key=lambda r: (-r["score"], -r["experience"]["candidate_relevant"], -r["required_coverage"]))
    for i, r in enumerate(results, 1):
        r["rank"], r["id"] = i, f"c{i}"
    return results
