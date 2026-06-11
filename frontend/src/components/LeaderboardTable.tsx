import { Link } from "react-router-dom";
import { LeaderboardEntry } from "../api/endpoints";
import { useAuth } from "../store/auth";
import { findCountry } from "../utils/countries";
import Flag from "./Flag";

function StatusMark({ set, correct }: { set: boolean; correct: boolean }) {
  if (correct)
    return (
      <span
        className="inline-flex items-center justify-center rounded bg-emerald-500 px-1.5 font-bold text-white"
        title="Засчитан"
      >
        ✓
      </span>
    );
  return set ? (
    <span className="text-emerald-600" title="Указан">✓</span>
  ) : (
    <span className="text-red-500" title="Не указан">✗</span>
  );
}

// English initials of the chosen scorer, e.g. "Kylian Mbappé" → "KM".
// Prefers a Latin name in parentheses ("Килиан Мбаппе (Kylian Mbappé)").
function scorerInitials(name: string): string {
  const paren = name.match(/\(([^)]*[A-Za-z][^)]*)\)/);
  const base = paren ? paren[1] : name;
  const latin = base.match(/[A-Za-z]+/g);
  const words = latin && latin.length ? latin : base.match(/[А-Яа-яЁё]+/g) || [];
  return words.slice(0, 2).map((w) => w[0].toUpperCase()).join("");
}

function ChampionCell({ e, started }: { e: LeaderboardEntry; started: boolean }) {
  if (!started) return <StatusMark set={e.has_champion} correct={e.champion_correct} />;
  if (!e.champion_team) return <span className="text-slate-300">—</span>;
  const c = findCountry(e.champion_team);
  return (
    <span
      className={`inline-flex ${e.champion_correct ? "rounded ring-2 ring-emerald-500" : ""}`}
      title={c?.ru ?? e.champion_team}
    >
      {c ? <Flag code={c.code} title={c.ru} /> : <span className="text-xs">{e.champion_team}</span>}
    </span>
  );
}

function ScorerCell({ e, started }: { e: LeaderboardEntry; started: boolean }) {
  if (!started) return <StatusMark set={e.has_scorer} correct={e.scorer_correct} />;
  if (!e.top_scorer_name) return <span className="text-slate-300">—</span>;
  return (
    <span
      className={`text-xs font-semibold ${e.scorer_correct ? "rounded bg-emerald-500 px-1 text-white" : "text-slate-600"}`}
      title={e.top_scorer_name}
    >
      {scorerInitials(e.top_scorer_name)}
    </span>
  );
}

export default function LeaderboardTable({
  entries,
  roomId,
  started = false,
}: {
  entries: LeaderboardEntry[];
  roomId: string;
  started?: boolean;
  isAdmin?: boolean;
}) {
  const me = useAuth((s) => s.user);
  // Колонка «участие подтверждено» нужна только до старта турнира — после
  // начала первого матча пропадает у всех (галочки остаются в админке комнаты).
  const showParticipation = !started;

  if (!entries.length)
    return <div className="text-slate-500">Пока нет участников.</div>;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b text-left text-slate-500">
          <th className="w-10 py-2">#</th>
          <th>Игрок</th>
          {showParticipation && (
            <th className="w-12 text-center" title="Участие подтверждено">✅</th>
          )}
          <th className="w-12 text-center" title="Чемпион">🏆</th>
          <th className="w-12 text-center" title="Бомбардир">⚽</th>
          <th className="text-center">Очки</th>
          <th className="w-16 text-center">Точных</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((e) => (
          <tr
            key={e.user_id}
            className={`border-b ${e.user_id === me?.id ? "bg-blue-50 font-semibold" : ""}`}
          >
            <td className="py-2">{e.place}</td>
            <td className="flex items-center gap-2 py-2">
              {e.avatar_url ? (
                <img src={e.avatar_url} className="h-6 w-6 rounded-full object-cover" />
              ) : (
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-300 text-xs">
                  {e.nickname[0]?.toUpperCase()}
                </div>
              )}
              <Link
                to={`/room/${roomId}/player/${e.user_id}`}
                className="hover:text-brand hover:underline"
              >
                {e.nickname}
              </Link>
            </td>
            {showParticipation && (
              <td className="text-center">
                {e.participation_confirmed ? (
                  <span className="text-emerald-600" title="Участие подтверждено">✓</span>
                ) : (
                  <span className="text-slate-300" title="Не подтверждено">—</span>
                )}
              </td>
            )}
            <td className="text-center">
              <ChampionCell e={e} started={started} />
            </td>
            <td className="text-center">
              <ScorerCell e={e} started={started} />
            </td>
            <td className="text-center">{e.total_points}</td>
            <td className="text-center">{e.exact_scores_count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
