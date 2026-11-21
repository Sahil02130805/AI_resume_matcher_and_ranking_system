export const scoreColor = (s) => (s >= 75 ? "var(--ok)" : s >= 50 ? "var(--warn)" : "var(--bad)");

export function Chip({ children, kind = "", title }) {
  return <span className={`chip ${kind}`} title={title}>{children}</span>;
}

export function Chips({ items, kind }) {
  if (!items?.length) return <span className="mut">—</span>;
  return items.map((x) => <Chip key={x} kind={kind}>{x}</Chip>);
}

export function Bar({ value, color }) {
  return <div className="bar"><i style={{ width: `${Math.min(100, value)}%`, background: color || scoreColor(value) }} /></div>;
}
