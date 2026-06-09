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
