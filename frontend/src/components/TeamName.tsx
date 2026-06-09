import { findCountry } from "../utils/countries";
import Flag from "./Flag";

interface Props {
  team: string | null | undefined;
  className?: string;
  /** Порядок флага: слева (по умолчанию) или справа от названия. */
  flagSide?: "left" | "right";
}

/** Название сборной на русском + флаг страны (картинкой). */
export default function TeamName({ team, className, flagSide = "left" }: Props) {
  if (!team) return null;
  const c = findCountry(team);
  const name = c?.ru ?? team;
  return (
    <span className={`inline-flex items-center gap-1.5 ${className ?? ""}`}>
      {c && flagSide === "left" && <Flag code={c.code} title={name} />}
      <span className="min-w-0 break-words">{name}</span>
      {c && flagSide === "right" && <Flag code={c.code} title={name} />}
    </span>
  );
}
