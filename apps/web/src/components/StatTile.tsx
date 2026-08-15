interface StatTileProps {
  label: string;
  value: string;
  unit?: string;
  hint?: string;
}

export default function StatTile({ label, value, unit, hint }: StatTileProps) {
  return (
    <div className="stat">
      <span className="stat__label">{label}</span>
      <span className="stat__value">{value}</span>
      {unit ? <span className="stat__unit">{unit}</span> : null}
      {hint ? <span className="stat__hint">{hint}</span> : null}
    </div>
  );
}
