import { useState } from "react";
import { parseJd, getSampleJd } from "../api";
import { Chips } from "./Chips";

export default function JobDescription({ text, setText, file, setFile, jd, setJd }) {
  const [err, setErr] = useState("");

  const extract = async () => {
    setErr("");
    try { setJd(await parseJd(text, file)); } catch (e) { setErr(e.message); }
  };
  const loadSample = async () => {
    const { jd_text } = await getSampleJd();
    setFile(null);
    setText(jd_text);
    setJd(await parseJd(jd_text, null));
  };

  return (
    <section className="card">
      <h2>1 · Job Description</h2>
      <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste a job description…" />
      <div className="row">
        <input type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files[0] || null)} />
        <button className="sec" onClick={extract}>Extract requirements</button>
        <button className="sec" onClick={loadSample}>Load sample JD</button>
      </div>
      {err && <p className="err">{err}</p>}
      {jd && (
        <div className="jdout">
          <b>{jd.title}</b>
          <div><span className="mut">Required </span><Chips items={jd.required_skills} kind="ok" /></div>
          <div><span className="mut">Preferred </span><Chips items={jd.preferred_skills} kind="pref" /></div>
          <div className="mut">
            Experience: {jd.min_experience_years ? `${jd.min_experience_years}${jd.max_experience_years ? "–" + jd.max_experience_years : "+"} yrs` : "not stated"}
            {" · "}Education: {jd.education_label}
            {jd.skill_requirements.filter((r) => r.min_years).map((r) => ` · ${r.label} ${r.min_years}+ yrs`).join("")}
          </div>
        </div>
      )}
    </section>
  );
}
