import { useQuery } from "@tanstack/react-query";
import { api, GroupStanding, StandingsMatch } from "../api/endpoints";
import { formatStage } from "../utils/stage";
import { formatDate, formatTime } from "../utils/dates";
import { LiveBadge } from "./MatchCard";
import TeamName from "./TeamName";

// Результат матча двух команд группы с точки зрения команды строки:
// "2:1" (свои голы первыми). null — матч не найден / не начался.
function cellFor(
  rowTeam: string,
  colTeam: string,
  matches: StandingsMatch[],
): { text: string; cls: string } | null {
  const m = matches.find(
    (x) =>
      (x.home_team === rowTeam && x.away_team === colTeam) ||
      (x.home_team === colTeam && x.away_team === rowTeam),
  );
  if (!m || m.home_score == null || m.away_score == null) return null;
  const mine = m.home_team === rowTeam ? m.home_score : m.away_score;
  const theirs = m.home_team === rowTeam ? m.away_score : m.home_score;
  if (m.status === "live")
    return { text: `${mine}:${theirs}`, cls: "text-red-600 font-semibold" };
  if (m.status !== "finished") return null;
  const cls =
    mine > theirs
      ? "bg-emerald-50 text-emerald-800"
      : mine === theirs
        ? "bg-amber-50 text-amber-800"
        : "bg-rose-50 text-rose-800";
  return { text: `${mine}:${theirs}`, cls };
}

function GroupTable({ group }: { group: GroupStanding }) {
  const order = group.teams.map((t) => t.team);
  return (
    <div className="card overflow-x-auto">
      <h3 className="mb-2 font-semibold">Группа {group.name}</h3>
      {/* min-w: на телефоне колонка с названием сжималась до нуля — теперь
          вместо этого таблица прокручивается горизонтально (overflow-x-auto
          на карточке). */}
      <table className="w-full min-w-[26rem] text-xs sm:text-sm">
        <thead>
          <tr className="border-b text-slate-500">
            <th className="py-1 pr-1 text-left">Команда</th>
            {order.map((_, i) => (
              <th key={i} className="w-10 text-center">
                {i + 1}
              </th>
            ))}
            <th className="w-10 text-center" title="Разница мячей">
              РМ
            </th>
            <th className="w-10 text-center" title="Очки">
              О
            </th>
          </tr>
        </thead>
        <tbody>
          {group.teams.map((t, row) => (
            <tr key={t.team} className="border-b last:border-b-0">
              <td className="max-w-0 truncate py-1.5 pr-1">
                <span className="mr-1 text-slate-400">{row + 1}.</span>
                <TeamName team={t.team} />
              </td>
              {order.map((opp, col) =>
                col === row ? (
                  <td key={opp} className="bg-slate-200 text-center" />
                ) : (
                  <Cell key={opp} cell={cellFor(t.team, opp, group.matches)} />
                ),
              )}
              <td className="text-center">
                {t.goal_diff > 0 ? `+${t.goal_diff}` : t.goal_diff}
              </td>
              <td className="text-center font-bold">{t.points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Cell({ cell }: { cell: { text: string; cls: string } | null }) {
  if (!cell) return <td className="text-center text-slate-300">—</td>;
  return <td className={`text-center ${cell.cls}`}>{cell.text}</td>;
}

function PlayoffMatchRow({ m }: { m: StandingsMatch }) {
  const hasScore = m.home_score != null && m.away_score != null;
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b py-2 text-sm last:border-b-0">
      <span className="w-28 shrink-0 text-xs text-slate-500">
        {formatDate(m.kickoff_at)} {formatTime(m.kickoff_at)}
      </span>
      <span className="flex min-w-0 flex-1 items-center justify-end">
        <TeamName team={m.home_team} flagSide="right" className="text-right" />
      </span>
      <span
        className={`shrink-0 px-1 text-center font-bold ${
          m.status === "live" ? "text-red-600" : ""
        }`}
      >
        {hasScore ? `${m.home_score}:${m.away_score}` : "—"}
      </span>
      <span className="flex min-w-0 flex-1 items-center">
        <TeamName team={m.away_team} />
      </span>
      {m.status === "live" && <LiveBadge />}
    </div>
  );
}

// Вкладка «ЧМ-2026»: реальное турнирное положение — таблицы групп (шахматка
// 4×4: результаты очных встреч, разница мячей, очки) и матчи плей-офф по
// стадиям. В режиме симуляции показывает симулированные результаты.
export default function WcStandings({ roomId }: { roomId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["standings", roomId],
    queryFn: () => api.standings(roomId),
    refetchInterval: 5 * 60_000,
  });

  if (isLoading) return <p className="text-slate-500">Загрузка…</p>;
  if (!data || (!data.groups.length && !data.playoff.length))
    return <p className="text-slate-500">Матчи ещё не добавлены.</p>;

  return (
    <div className="space-y-6">
      {data.groups.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-2">
          {data.groups.map((g) => (
            <GroupTable key={g.name} group={g} />
          ))}
        </div>
      )}

      {data.playoff.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Плей-офф</h2>
          {data.playoff.map((st) => (
            <section key={st.stage} className="card">
              <h3 className="mb-1 font-semibold">{formatStage(st.stage)}</h3>
              {st.matches.map((m) => (
                <PlayoffMatchRow key={m.id} m={m} />
              ))}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
