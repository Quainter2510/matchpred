// Бейдж бонусного коэффициента матча/тура. ×1 не показывается.
export default function MultiplierBadge({
  value,
  large = false,
}: {
  value: number;
  large?: boolean;
}) {
  if (value === 1) return null;
  const style =
    value === 0
      ? "bg-slate-500 text-white"
      : value === 2
        ? "bg-amber-400 text-amber-950"
        : "bg-fuchsia-600 text-white";
  return (
    <span
      title={
        value === 0
          ? "Очки за этот матч не начисляются"
          : `Бонус: очки умножаются на ${value}`
      }
      className={`inline-flex shrink-0 items-center rounded-md font-extrabold tracking-wide ${style} ${
        large ? "px-2 py-0.5 text-sm" : "px-1.5 py-0.5 text-xs"
      }`}
    >
      ×{value}
    </span>
  );
}
