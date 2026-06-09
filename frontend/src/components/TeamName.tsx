import { findCountry } from "../utils/countries";

interface Props {
  team: string | null | undefined;
  className?: string;
  /** Порядок флага: слева (по умолчанию) или справа от названия. */
  flagSide?: "left" | "right";
}

/** Название сборной на русском + флаг страны. */
export default function TeamName({ team, className, flagSide = "left" }: Props) {
  if (!team) return null;
  const c = findCountry(team);
  const name = c?.ru ?? team;
  const flag = c?.flag;
  return (
    <span className={`inline-flex items-center gap-1.5 ${className ?? ""}`}>
      {flag && flagSide === "left" && <span aria-hidden>{flag}</span>}
      <span>{name}</span>
      {flag && flagSide === "right" && <span aria-hidden>{flag}</span>}
    </span>
  );
}
