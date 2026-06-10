/**
 * Флаг страны через пакет flag-icons (SVG из бандла, не внешние картинки).
 * Внешний flagcdn блокировался в мобильных браузерах/вебвью — локальные ассеты
 * грузятся всегда. Код 4:3 (`us`, `br`, `gb-eng`, …) → класс `fi fi-<code>`.
 */
export default function Flag({ code, title }: { code: string; title?: string }) {
  return (
    <span
      title={title}
      className={`fi fi-${code} h-[15px] w-5 shrink-0 rounded-[2px]`}
      style={{ backgroundSize: "cover" }}
    />
  );
}
