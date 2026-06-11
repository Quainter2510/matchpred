import { Fragment, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api, TourPlayerMatch } from "../api/endpoints";
import MatchCard from "../components/MatchCard";
import TeamName from "../components/TeamName";
import { useAuth } from "../store/auth";
import { formatDate, isPast } from "../utils/dates";
import { classifyPrediction, HIT_BADGE, HIT_BG } from "../utils/scoring";

function isFinished(m: TourPlayerMatch): boolean {
  return m.status === "finished" && m.home_score != null && m.away_score != null;
}

// Подсветка строки матча в раскрытом списке — та же схема, что и везде.
function itemTint(m: TourPlayerMatch): string {
  if (!isFinished(m)) return "";
  if (m.predicted_home == null || m.predicted_away == null) return HIT_BG.miss;
  return HIT_BG[
    classifyPrediction(m.predicted_home, m.predicted_away, m.home_score!, m.away_score!)
  ];
}

// Раскрытый список матчей игрока: матч, счёт, прогноз, очки.
function PlayerMatches({ matches }: { matches: TourPlayerMatch[] }) {
  return (
    <div className="space-y-1 py-2">
      {matches.map((m) => {
        const fin = isFinished(m);
        const live = m.started && !fin;
        const hasPred = m.predicted_home != null && m.predicted_away != null;
        return (
          <div
            key={m.match_id}
            className={`flex items-center gap-2 rounded px-2 py-1 text-xs sm:text-sm ${itemTint(m)}`}
          >
            <span className="flex min-w-0 flex-1 justify-end">
              <TeamName team={m.home_team} flagSide="right" className="truncate text-right" />
            </span>
            <span
              className={`w-12 shrink-0 text-center font-bold tabular-nums ${
                live ? "text-red-600" : ""
              }`}
            >
              {m.home_score != null && m.away_score != null
                ? `${m.home_score}:${m.away_score}`
                : "—:—"}
            </span>
            <span className="flex min-w-0 flex-1">
              <TeamName team={m.away_team} className="truncate" />
            </span>
            <span className="w-16 shrink-0 text-center text-slate-600">
              {hasPred ? (
                <>
                  прогноз <b className="tabular-nums">{m.predicted_home}:{m.predicted_away}</b>
                </>
              ) : (
                "—"
              )}
            </span>
            <span className="w-16 shrink-0 text-right">
              {!m.started ? (
                <span className="text-[10px] uppercase text-slate-400">не начался</span>
              ) : live ? (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase text-red-600">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-600" />
                  идёт
                </span>
              ) : m.points_awarded != null ? (
                <span
                  className={`rounded px-1.5 py-0.5 font-bold tabular-nums ${
                    HIT_BADGE[
                      hasPred
                        ? classifyPrediction(
                            m.predicted_home!,
                            m.predicted_away!,
                            m.home_score!,
                            m.away_score!
                          )
                        : "miss"
                    ]
                  }`}
                >
                  +{m.points_awarded}
                </span>
              ) : (
                // Завершён, но прогноза не было — 0 очков.
                <span className="font-semibold text-rose-600">0</span>
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function Tour() {
  const { roomId, date } = useParams<{ roomId: string; date: string }>();
  const me = useAuth((s) => s.user);
  const [open, setOpen] = useState<Set<string>>(new Set());
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

  const players = standings.data || [];
  const allOpen = players.length > 0 && open.size >= players.length;
  const toggleOne = (uid: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(uid)) next.delete(uid);
      else next.add(uid);
      return next;
    });
  const toggleAll = () =>
    setOpen(allOpen ? new Set() : new Set(players.map((p) => p.user_id)));

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

      {started && players.length > 0 && (
        <section className="card">
          <div className="mb-3 flex items-center gap-2">
            <h2 className="text-lg font-semibold">Итоги тура</h2>
            <button
              onClick={toggleAll}
              className="rounded border border-slate-300 px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-100"
              title={allOpen ? "Свернуть всех игроков" : "Раскрыть всех игроков"}
            >
              {allOpen ? "Свернуть всех ▴" : "Раскрыть всех ▾"}
            </button>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-slate-500">
                <th className="w-10 py-2">#</th>
                <th>Игрок</th>
                <th className="w-20 text-center" title="Сделано прогнозов">
                  Прогнозы
                </th>
                <th className="w-16 text-center" title="Точных счетов">
                  Точных
                </th>
                <th className="w-14 text-right">Очки</th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody>
              {players.map((p, i) => (
                <Fragment key={p.user_id}>
                  <tr
                    className={`border-b ${
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
                    <td className="text-center">
                      <button
                        onClick={() => toggleOne(p.user_id)}
                        className="rounded px-1.5 py-0.5 text-slate-500 hover:bg-slate-100"
                        title={
                          open.has(p.user_id)
                            ? "Свернуть матчи игрока"
                            : "Показать матчи игрока"
                        }
                      >
                        {open.has(p.user_id) ? "▴" : "▾"}
                      </button>
                    </td>
                  </tr>
                  {open.has(p.user_id) && (
                    <tr className="border-b bg-slate-50/60">
                      <td colSpan={6} className="px-2">
                        <PlayerMatches matches={p.matches} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
