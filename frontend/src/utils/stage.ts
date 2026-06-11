// Преобразование технического кода стадии (из API-Football, напр. "group_a_-_1",
// "round_of_16", "final") в человекочитаемую подпись на русском.

const KNOCKOUT: { re: RegExp; label: string }[] = [
  { re: /round[_\s-]*of[_\s-]*32|1\/16/, label: "1/16 финала" },
  { re: /round[_\s-]*of[_\s-]*16|1\/8/, label: "1/8 финала" },
  { re: /quarter|1\/4/, label: "1/4 финала" },
  { re: /semi|1\/2/, label: "1/2 финала" },
  { re: /3rd[_\s-]*place|third[_\s-]*place|bronze/, label: "Матч за 3-е место" },
  { re: /final/, label: "Финал" },
];

export function formatStage(
  stage: string | null | undefined,
  groupName?: string | null,
): string {
  if (!stage) return "";
  const s = stage.toLowerCase().trim();
  // Принимаем только короткую метку группы (буква/число), а не служебные
  // строки из standings вроде "Ranking of third-placed teams".
  const raw = groupName?.trim();
  const grp = raw && /^[a-z0-9]{1,3}$/i.test(raw) ? raw.toUpperCase() : undefined;

  // Группа с буквой: "group_a_-_1", "group_a", "group_b_2" → "Группа A тур 1".
  const lettered = s.match(/group[_\s-]*([a-l])(?:[_\s-]+(\d+))?/);
  if (lettered) {
    const letter = lettered[1].toUpperCase();
    return lettered[2] ? `Группа ${letter} тур ${lettered[2]}` : `Группа ${letter}`;
  }

  // Групповой этап без буквы в коде: "group_stage_-_1", "group_-_1", "group_1".
  // Букву группы (если известна — из standings) подставляем отдельно.
  const groupTour = s.match(/group(?:[_\s-]*stage)?[_\s-]+(\d+)/);
  if (groupTour) {
    return grp
      ? `Группа ${grp} тур ${groupTour[1]}`
      : `Групповой этап, тур ${groupTour[1]}`;
  }

  for (const { re, label } of KNOCKOUT) {
    if (re.test(s)) return label;
  }

  if (/group/.test(s)) return grp ? `Группа ${grp}` : "Групповой этап";

  // Фолбэк: убираем подчёркивания/дефисы, делаем первую букву заглавной.
  const pretty = s.replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
  return pretty.charAt(0).toUpperCase() + pretty.slice(1);
}
