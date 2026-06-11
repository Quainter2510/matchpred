import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/endpoints";
import MatchCard from "../components/MatchCard";
import { useAuth } from "../store/auth";
import { formatDate, isPast } from "../utils/dates";

export default function Tour() {
  const { roomId, date } = useParams<{ roomId: string; date: string }>();
  const me = useAuth((s) => s.user);
  const { data, isLoading } = useQuery({
    queryKey: ["matches", roomId, date],
    queryFn: () => api.matchesByDate(roomId!, date!),
    enabled: !!roomId && !!date,
    // Бэкенд опрашивает API-Football каждые 5 минут — подтягиваем live-счёт
    // и обновлённые очки без перезагрузки страницы.
    refetchInterval: 60_000,
  });

  // Тур начался — показываем таблицу итогов (очки всех участников за день).
  const started = !!data?.length && isPast(data[0].kickoff_at);
  const standings = useQuery({
    queryKey: ["tour-leaderboard", roomId, date],
    queryFn: () => api.tourLeaderboard(roomId!, date!),
    enabled: !!roomId && !!date && started,
    refetchInterval: 60_000,
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link to={`/room/${roomId}?tab=predictions`} className="btn-ghost">
          ← Назад
        </Link>
        <h1 className="text-2xl font-bold">{date && formatDate(date)}</h1>
      </div>
      {isLoading ? (
        <p className="text-slate-500">Загрузка…</p>
      ) : !data?.length ? (
        <p className="text-slate-500">Нет матчей.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {data.map((m) => (
            <MatchCard key={m.id} match={m} roomId={roomId!} />
          ))}
        </div>
      )}

      {started && standings.data && standings.data.length > 0 && (
        <section className="card">
          <h2 className="mb-3 text-lg font-semibold">Итоги тура</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-slate-500">
                <th className="w-10 py-2">#</th>
                <th>Игрок</th>
                <th className="w-24 text-center" title="Сделано прогнозов">
                  Прогнозы
                </th>
                <th className="w-16 text-center" title="Точных счетов">
                  Точных
                </th>
                <th className="w-16 text-right">Очки</th>
              </tr>
            </thead>
            <tbody>
              {standings.data.map((p, i) => (
                <tr
                  key={p.user_id}
                  className={`border-b last:border-b-0 ${
                    p.user_id === me?.id ? "bg-blue-50 font-semibold" : ""
                  }`}
                >
                  <td className="py-2">{i + 1}</td>
                  <td className="flex items-center gap-2 py-2">
                    {p.avatar_url ? (
                      <img
                        src={p.avatar_url}
                        className="h-6 w-6 rounded-full object-cover"
                      />
                    ) : (
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-300 text-xs">
                        {p.nickname[0]?.toUpperCase()}
                      </div>
                    )}
                    <Link
                      to={`/room/${roomId}/player/${p.user_id}`}
                      className="hover:text-brand hover:underline"
                    >
                      {p.nickname}
                    </Link>
                  </td>
                  <td
                    className={`text-center ${
                      p.predictions_count < p.match_count ? "text-rose-600" : ""
                    }`}
                  >
                    {p.predictions_count}/{p.match_count}
                  </td>
                  <td className="text-center">{p.exact_count}</td>
                  <td className="text-right text-lg font-extrabold tabular-nums">
                    {p.points}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
