interface Props {
  value: number | "";
  onChange: (v: number | "") => void;
  disabled?: boolean;
}

export default function ScoreInput({ value, onChange, disabled }: Props) {
  return (
    <input
      type="number"
      min={0}
      max={20}
      disabled={disabled}
      value={value}
      onChange={(e) => {
        const v = e.target.value;
        if (v === "") return onChange("");
        const n = Math.max(0, Math.min(20, parseInt(v, 10)));
        onChange(Number.isNaN(n) ? "" : n);
      }}
      className="w-16 rounded-lg border border-slate-300 px-2 py-2 text-center text-xl focus:border-brand focus:outline-none disabled:bg-slate-100"
    />
  );
}
