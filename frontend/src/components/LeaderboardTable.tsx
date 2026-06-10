import { Link } from "react-router-dom";
import { LeaderboardEntry } from "../api/endpoints";
import { useAuth } from "../store/auth";

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

export default function LeaderboardTable({
  entries,
  roomId,
}: {
  entries: LeaderboardEntry[];
  roomId: string;
}) {
  const me = useAuth((s) => s.user);
  if (!entries.length)
    return <div className="text-slate-500">Пока нет участников.</div>;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b text-left text-slate-500">
          <th className="py-2 w-10">#</th>
          <th>Игрок</th>
          <th className="text-center w-12" title="Участие подтверждено">✅</th>
          <th className="text-center w-12" title="Чемпион">🏆</th>
          <th className="text-center w-12" title="Бомбардир">⚽</th>
          <th className="text-center">Очки</th>
          <th className="text-center w-16">Точных</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((e) => (
          <tr
            key={e.user_id}
            className={`border-b ${
              e.user_id === me?.id ? "bg-blue-50 font-semibold" : ""
            }`}
          >
            <td className="py-2">{e.place}</td>
            <td className="flex items-center gap-2 py-2">
              {e.avatar_url ? (
                <img src={e.avatar_url} className="h-6 w-6 rounded-full" />
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
            <td className="text-center">
              {e.participation_confirmed ? (
                <span className="text-emerald-600" title="Участие подтверждено">✓</span>
              ) : (
                <span className="text-slate-300" title="Не подтверждено">—</span>
              )}
            </td>
            <td className="text-center"><StatusMark set={e.has_champion} correct={e.champion_correct} /></td>
            <td className="text-center"><StatusMark set={e.has_scorer} correct={e.scorer_correct} /></td>
            <td className="text-center">{e.total_points}</td>
            <td className="text-center">{e.exact_scores_count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
