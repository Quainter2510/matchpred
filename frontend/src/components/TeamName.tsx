import { findCountry } from "../utils/countries";
import { useTeamsMap } from "../utils/useTeams";
import Flag from "./Flag";

interface Props {
  team: string | null | undefined;
  className?: string;
  /** Порядок флага/логотипа: слева (по умолчанию) или справа от названия. */
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

function ClubLogo({ src, title }: { src: string; title: string }) {
  return (
    <img
      src={src}
      alt={title}
      title={title}
      loading="lazy"
      className="inline-block h-4 w-4 shrink-0 object-contain"
    />
  );
}

/** Название команды на русском + флаг (сборные) или логотип (клубы). */
export default function TeamName({ team, className, flagSide = "left", short = false }: Props) {
  const teams = useTeamsMap();
  if (!team) return null;

  // Сборные (ЧМ) — русское имя из countries.ts + флаг.
  const country = findCountry(team);
  if (country) {
    const name = country.ru;
    const display = short ? SHORT_NAMES[name] ?? name : name;
    return (
      <span className={`inline-flex max-w-full items-center gap-1.5 ${className ?? ""}`}>
        {flagSide === "left" && <Flag code={country.code} title={name} />}
        <span className="min-w-0 break-words">{display}</span>
        {flagSide === "right" && <Flag code={country.code} title={name} />}
      </span>
    );
  }

  // Клубы — русское имя + логотип из справочника /teams (фолбэк — исходная строка).
  const info = teams.get(team.trim().toLowerCase());
  const name = info?.name_ru ?? team;
  const logo = info?.logo || null;
  return (
    <span className={`inline-flex max-w-full items-center gap-1.5 ${className ?? ""}`}>
      {logo && flagSide === "left" && <ClubLogo src={logo} title={name} />}
      <span className="min-w-0 break-words">{name}</span>
      {logo && flagSide === "right" && <ClubLogo src={logo} title={name} />}
    </span>
  );
}
