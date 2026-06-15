import { findCountry } from "../utils/countries";
import Flag from "./Flag";

interface Props {
  team: string | null | undefined;
  className?: string;
  /** Порядок флага: слева (по умолчанию) или справа от названия. */
  flagSide?: "left" | "right";
  /** Сокращённые названия длинных стран (для тесных таблиц, напр. групп ЧМ). */
  short?: boolean;
}

// Сокращения только для самых длинных названий — используются при short.
const SHORT_NAMES: Record<string, string> = {
  "Новая Зеландия": "Н. Зеландия",
  "Босния и Герцеговина": "Босн. и Герц.",
  "Саудовская Аравия": "С. Аравия",
};

/** Название сборной на русском + флаг страны (картинкой). */
export default function TeamName({ team, className, flagSide = "left", short = false }: Props) {
  if (!team) return null;
  const c = findCountry(team);
  const name = c?.ru ?? team;
  const display = short ? SHORT_NAMES[name] ?? name : name;
  return (
    <span className={`inline-flex max-w-full items-center gap-1.5 ${className ?? ""}`}>
      {c && flagSide === "left" && <Flag code={c.code} title={name} />}
      <span className="min-w-0 break-words">{display}</span>
      {c && flagSide === "right" && <Flag code={c.code} title={name} />}
    </span>
  );
}
