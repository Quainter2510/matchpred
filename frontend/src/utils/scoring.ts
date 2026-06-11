// Client-side preview of points. The authoritative scoring lives on the backend.
export function previewPoints(
  ph: number,
  pa: number,
  ah: number,
  aa: number
): number {
  if (ph === ah && pa === aa) return 5;
  const pd = ph - pa;
  const ad = ah - aa;
  if (pd === ad) return 2;
  if (Math.sign(pd) === Math.sign(ad)) return 1;
  return 0;
}

// Категория попадания прогноза — не зависит от очков комнаты и коэффициентов,
// сравниваются сами счета. Единая цветовая схема по всему приложению:
// точный — зелёный, разница — синий, исход — янтарный, промах — красный.
export type HitKind = "exact" | "diff" | "outcome" | "miss";

export function classifyPrediction(
  ph: number,
  pa: number,
  ah: number,
  aa: number
): HitKind {
  if (ph === ah && pa === aa) return "exact";
  const pd = ph - pa;
  const ad = ah - aa;
  if (pd === ad) return "diff";
  if (Math.sign(pd) === Math.sign(ad)) return "outcome";
  return "miss";
}

// Заливки приглушённые (полупрозрачные -50), чтобы текст оставался главным.
export const HIT_BG: Record<HitKind, string> = {
  exact: "bg-emerald-50/60",
  diff: "bg-sky-50/60",
  outcome: "bg-amber-50/60",
  miss: "bg-rose-50/60",
};

export const HIT_CARD: Record<HitKind, string> = {
  exact: "border-emerald-200 bg-emerald-50/60",
  diff: "border-sky-200 bg-sky-50/60",
  outcome: "border-amber-200 bg-amber-50/60",
  miss: "border-rose-200 bg-rose-50/60",
};
