import { TeamFormMatch } from "../api/endpoints";
import TeamName from "./TeamName";

// Последние сыгранные матчи сборной (страница прогноза): буква результата
// (В/Н/П), счёт со стороны команды, соперник, дата и турнир.

function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
  });
}

const RESULT = {
  win: { letter: "В", cls: "bg-emerald-500" },
  draw: { letter: "Н", cls: "bg-slate-400" },
  loss: { letter: "П", cls: "bg-rose-500" },
} as const;

export default function TeamForm({
  team,
  matches,
}: {
  team: string;
  matches: TeamFormMatch[];
}) {
  if (!matches.length)
    return (
      <div>
        <TeamName team={team} className="text-sm font-semibold" />
        <p className="mt-1 text-xs text-slate-400">Сыгранных матчей нет.</p>
      </div>
    );

  return (
    <div>
      <TeamName team={team} className="text-sm font-semibold" />
      <ul className="mt-1.5 space-y-1">
        {matches.map((m) => {
          const isHome = m.home_team === team;
          const mine = isHome ? m.home_score : m.away_score;
          const theirs = isHome ? m.away_score : m.home_score;
          const opponent = isHome ? m.away_team : m.home_team;
          const r =
            mine > theirs ? RESULT.win : mine === theirs ? RESULT.draw : RESULT.loss;
          return (
            <li
              key={`${m.kickoff_at}-${opponent}`}
              className="flex items-center gap-2 text-sm"
            >
              <span
                className={`flex h-5 w-5 shrink-0 items-center justify-center rounded text-xs font-bold text-white ${r.cls}`}
              >
                {r.letter}
              </span>
              <span className="w-8 shrink-0 text-center font-semibold tabular-nums">
                {mine}:{theirs}
              </span>
              <TeamName team={opponent} className="min-w-0 flex-1 truncate" />
              <span className="shrink-0 text-right text-xs text-slate-400">
                {shortDate(m.kickoff_at)}
                {m.competition ? ` · ${m.competition}` : ""}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
