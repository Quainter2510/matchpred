interface Props {
  value: number;
  onChange: (v: number) => void;
  disabled?: boolean;
  label?: string;
}

const MIN = 0;
const MAX = 20;

/** Крупный счётчик голов с кнопками − / + (удобно на телефоне, без клавиатуры). */
export default function ScoreStepper({ value, onChange, disabled, label }: Props) {
  const clamp = (n: number) => Math.max(MIN, Math.min(MAX, n));
  const btn =
    "flex h-11 w-11 items-center justify-center rounded-full border border-slate-300 text-2xl font-bold leading-none text-slate-700 select-none active:bg-slate-100 disabled:opacity-40";

  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        aria-label={label ? `${label}: минус` : "минус"}
        className={btn}
        disabled={disabled || value <= MIN}
        onClick={() => onChange(clamp(value - 1))}
      >
        −
      </button>
      <span className="w-8 text-center text-3xl font-bold tabular-nums">
        {value}
      </span>
      <button
        type="button"
        aria-label={label ? `${label}: плюс` : "плюс"}
        className={btn}
        disabled={disabled || value >= MAX}
        onClick={() => onChange(clamp(value + 1))}
      >
        +
      </button>
    </div>
  );
}
