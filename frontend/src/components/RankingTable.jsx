import { useState } from "react";
import { Bar, Chip, Chips, scoreColor } from "./Chips";

function exportCsv(cands) {
  const q = (s) => `"${String(s ?? "").replace(/"/g, '""')}"`;
  const rows = [["Rank", "Candidate", "Email", "Total yrs", "Relevant yrs", "Match %", "Matched skills", "Missing skills"],
    ...cands.map((c) => [c.rank, c.name, c.email, c.experience.candidate_total, c.experience.candidate_relevant, c.score,
      c.matched_skills.map((m) => m.skill).join("; "), c.missing_skills.map((m) => m.skill).join("; ")])];
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([rows.map((r) => r.map(q).join(",")).join("\n")], { type: "text/csv" }));
  a.download = "ranking.csv";
  a.click();
}

export default function RankingTable({ data, selected, onSelect }) {
  const [min, setMin] = useState(0);
  const [sortKey, setSortKey] = useState("rank");
  const keyFn = { rank: (c) => c.rank, score: (c) => -c.score, exp: (c) => -c.experience.candidate_relevant, name: (c) => c.name };
  const list = data.candidates.filter((c) => c.score >= min).sort((a, b) => {
    const x = keyFn[sortKey](a), y = keyFn[sortKey](b);
    return x < y ? -1 : x > y ? 1 : 0;
  });
  const th = (k, label) => <th className="sortable" onClick={() => setSortKey(k)}>{label}{sortKey === k ? " ▾" : ""}</th>;

  return (
    <section className="card">
      <h2>3 · Ranking <span className="mut">({list.length} of {data.candidates.length})</span></h2>
      <div className="row tight">
        <label>Min match <input type="range" min="0" max="100" value={min} onChange={(e) => setMin(+e.target.value)} /> <b>{min}</b>%</label>
        <button className="sec" onClick={() => exportCsv(data.candidates)}>Export CSV</button>
      </div>
      <div className="scroll">
        <table>
          <thead><tr>{th("rank", "#")}{th("name", "Candidate")}{th("exp", "Experience")}{th("score", "Match %")}<th>Matched skills</th><th>Missing (required)</th></tr></thead>
          <tbody>
            {list.map((c) => {
              const miss = c.missing_skills.filter((m) => m.required).map((m) => m.skill);
              return (
                <tr key={c.id} className={selected === c.id ? "sel" : ""} onClick={() => onSelect(c.id)}>
                  <td>{c.rank}</td>
                  <td><b>{c.name}</b><div className="mut small">{c.current_title || c.filename}</div></td>
                  <td>{c.experience.candidate_total} yrs<div className="mut small">{c.experience.candidate_relevant} relevant</div></td>
                  <td style={{ minWidth: 110 }}><b style={{ color: scoreColor(c.score) }}>{Math.round(c.score)}%</b><Bar value={c.score} /></td>
                  <td>
                    {c.matched_skills.slice(0, 6).map((m) => <Chip key={m.skill} kind={m.type === "exact" && m.credit >= 0.95 ? "ok" : "rel"}>{m.skill}</Chip>)}
                    {c.matched_skills.length > 6 && <span className="mut"> +{c.matched_skills.length - 6}</span>}
                  </td>
                  <td><Chips items={miss.slice(0, 4)} kind="bad" />{miss.length > 4 && <span className="mut"> +{miss.length - 4}</span>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {data.errors?.length > 0 && (
        <div className="err small">{data.errors.map((e) => <div key={e.filename}>{e.filename}: {e.error}</div>)}</div>
      )}
    </section>
  );
}
