import { Bar, Chip, scoreColor } from "./Chips";

const LABELS = { skills: "Skills coverage", semantic: "Semantic fit", experience: "Experience", education: "Education" };

function skillTitle(m) {
  const bits = [];
  if (m.type !== "exact") bits.push(`via ${m.matched_with} (${m.type})`);
  if (m.years) bits.push(`${m.years} yrs`);
  if (m.evidence) bits.push(m.evidence);
  if (m.last_used) bits.push(`last used ${m.last_used}`);
  return bits.concat(m.notes || []).join(" · ");
}

export default function CandidateDetail({ c }) {
  const e = c.experience;
  return (
    <section className="card detail">
      <div className="grid2">
        <div>
          <h2>{c.name} <span className="mut">· rank #{c.rank}</span></h2>
          <div className="mut small">{c.current_title && `${c.current_title} · `}{c.email || "no email"} · {c.phone || "no phone"} · {c.filename}</div>
          {c.warnings?.length > 0 && <div className="warn small">⚠ {c.warnings.join(" ")}</div>}
          {c.summary && <p>{c.summary}</p>}

          <h3>Education</h3>
          <ul>{c.education.length ? c.education.map((x, i) => (
            <li key={i}>{x.degree}{x.field && ` in ${x.field}`}{x.institution && ` — ${x.institution}`}{x.year && ` (${x.year})`}</li>
          )) : <li className="mut">Not detected</li>}</ul>

          <h3>Experience comparison</h3>
          <table className="mini"><tbody>
            <tr><td>Required</td><td>{e.required ? `${e.required}${e.required_max ? "–" + e.required_max : "+"} yrs` : "not specified"}</td></tr>
            <tr><td>Candidate total</td><td>{e.candidate_total} yrs</td></tr>
            <tr><td>Relevant to this JD</td><td><b>{e.candidate_relevant} yrs</b> {e.verdict && <Chip kind={e.verdict === "meets" ? "ok" : "bad"}>{e.verdict}</Chip>}</td></tr>
          </tbody></table>

          <h3>Work history</h3>
          <ul>{c.jobs.map((j, i) => (
            <li key={i}>
              <b>{j.title || j.header}</b>{j.company && ` · ${j.company}`} <span className="mut small">{j.start} → {j.end}{j.is_intern ? " · internship (×0.5)" : ""}</span>
              <div><Chip kind={j.relevance >= 0.5 ? "ok" : ""}>{Math.round(j.relevance * 100)}% relevant</Chip> <span className="mut small">{j.matched_skills.join(", ")}</span></div>
            </li>
          ))}</ul>
        </div>

        <div>
          <div className="big" style={{ color: scoreColor(c.score) }}>{c.score}<small className="mut">/100</small></div>
          {c.raw_score > c.score && <div className="mut small">Uncapped score {c.raw_score} — a ceiling was applied (see reasons)</div>}
          {Object.entries(c.breakdown).map(([k, v]) => (
            <div className="row tight" key={k}>
              <span className="lbl">{LABELS[k]}</span><div style={{ flex: 1 }}><Bar value={v.score} /></div>
              <span className="mut small calc">{v.score}% × {Math.round(v.weight * 100)}% = <b>{v.points}</b></span>
            </div>
          ))}

          <h3>Matched skills <span className="mut small">(hover for evidence)</span></h3>
          <div>{c.matched_skills.map((m) => (
            <Chip key={m.skill} title={skillTitle(m)} kind={`${m.type === "exact" && m.credit >= 0.95 ? "ok" : "rel"} ${m.required ? "" : "pref"}`}>
              {m.skill}{m.type !== "exact" && ` ≈ ${m.matched_with}`}{m.credit < 0.95 && ` · ${Math.round(m.credit * 100)}%`}
            </Chip>
          ))}</div>

          <h3>Missing skills</h3>
          <div>{c.missing_skills.length ? c.missing_skills.map((m) => (
            <Chip key={m.skill} kind={`bad ${m.required ? "" : "pref"}`}>{m.skill}{!m.required && " (preferred)"}</Chip>
          )) : <span className="mut">None</span>}</div>

          <h3>Why this score</h3>
          <ul>{c.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>

          {c.evidence?.strong?.length > 0 && (<>
            <h3>Best-matching resume evidence</h3>
            <ul className="small">{c.evidence.strong.map((x, i) => (
              <li key={i}><span className="mut">JD:</span> {x.requirement}<br /><span className="mut">Resume ({Math.round(x.similarity * 100)}%):</span> “{x.resume_text}”</li>
            ))}</ul>
          </>)}
          {c.evidence?.weak?.length > 0 && (<>
            <h3>Requirements with weak evidence</h3>
            <ul className="small">{c.evidence.weak.map((x, i) => <li key={i}>{x.requirement}</li>)}</ul>
          </>)}
          <div className="mut small">Similarity backend: {c.similarity_backend}</div>
        </div>
      </div>
    </section>
  );
}
