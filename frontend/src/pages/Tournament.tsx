import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, MatchDay, RoomScoring } from "../api/endpoints";
import LeaderboardTable from "../components/LeaderboardTable";
import MultiplierBadge from "../components/MultiplierBadge";
import WcStandings from "../components/WcStandings";
import SpecialPredictionCard from "./SpecialPredictionCard";
import { useAuth } from "../store/auth";
import { formatDate, isPast, nowMs } from "../utils/dates";

const DAY_MS = 86400000;

// Подсветка тура:
//  • зелёный  — прогноз дан на все матчи;
//  • красный  — матчи начались, а прогноз неполный (пропущен);
//  • жёлтый   — до начала дня ≤ 2 дней и прогноз неполный;
//  • нейтральный — времени ещё много.
function dayStatus(d: MatchDay): { cls: string; label: string; labelCls: string } {
  const allPredicted =
    d.match_count > 0 && d.my_predictions_count >= d.match_count;
  if (allPredicted)
    return {
      cls: "border-emerald-300 bg-emerald-50 hover:bg-emerald-100",
      label: "Прогноз готов",
      labelCls: "text-emerald-700",
    };
  if (isPast(d.first_kickoff_at))
    return {
      cls: "border-red-300 bg-red-50 hover:bg-red-100",
      label: "Прогноз пропущен",
      labelCls: "text-red-700",
    };
  const msToStart = new Date(d.first_kickoff_at).getTime() - nowMs();
  if (msToStart <= 2 * DAY_MS)
    return {
      cls: "border-amber-300 bg-amber-50 hover:bg-amber-100",
      label: "Скоро дедлайн",
      labelCls: "text-amber-700",
    };
  return { cls: "hover:bg-slate-50", label: "", labelCls: "" };
}

// Стандартный регламент, когда админ не заполнил свой текст.
function defaultRules(s: RoomScoring | null | undefined): string {
  if (!s) return "Регламент не заполнен.";
  return [
    "Начисление очков:",
    `• точный счёт — ${s.points_exact}`,
    `• разница мячей — ${s.points_diff}`,
    `• исход (победитель/ничья) — ${s.points_outcome}`,
    `• чемпион турнира — ${s.points_champion}`,
    `• лучший бомбардир — ${s.points_scorer}`,
  ].join("\n");
}

export default function Tournament() {
  const { roomId } = useParams<{ roomId: string }>();
  // Remember the last opened competition so the app reopens it next time.
  useEffect(() => {
    if (roomId) localStorage.setItem("last_room_id", roomId);
  }, [roomId]);
  const room = useQuery({
    queryKey: ["room", roomId],
    queryFn: () => api.roomDetail(roomId!),
    enabled: !!roomId,
  });
  const lb = useQuery({
    queryKey: ["leaderboard", roomId],
    queryFn: () => api.leaderboard(roomId!),
    enabled: !!roomId,
  });
  const days = useQuery({
    queryKey: ["days", roomId],
    queryFn: () => api.matchDays(roomId!),
    enabled: !!roomId,
  });

  const me = useAuth((st) => st.user);
  const isRoomAdmin = room.data?.my_role === "admin";
  const isAdmin = me?.system_role === "superadmin" || isRoomAdmin;
  const archived = room.data && !room.data.is_active;
  const started = !!room.data?.first_match_at && isPast(room.data.first_match_at);
  // Активная вкладка живёт в URL (?tab=…), чтобы «назад» из тура/матча
  // возвращал на ту же вкладку, а не на таблицу по умолчанию.
  const [searchParams, setSearchParams] = useSearchParams();
  const rawTab = searchParams.get("tab");
  const tab: "table" | "predictions" | "wc" =
    rawTab === "predictions" || rawTab === "wc" ? rawTab : "table";
  const setTab = (id: typeof tab) =>
    setSearchParams(id === "table" ? {} : { tab: id }, { replace: true });
  const [showRules, setShowRules] = useState(false);
  const rulesText = room.data?.rules_text || defaultRules(room.data?.scoring);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/rooms" className="text-sm text-slate-500 hover:underline">
            ← Все соревнования
          </Link>
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            {room.data?.name || "Соревнование"}
            {archived && <span className="text-sm font-normal text-slate-400">(архив)</span>}
            {room.data && (
              <button
                onClick={() => setShowRules(true)}
                title="Регламент соревнования"
                aria-label="Регламент соревнования"
                className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-slate-300 text-xs font-semibold italic text-slate-500 hover:bg-slate-100"
              >
                i
              </button>
            )}
          </h1>
        </div>
        {isRoomAdmin && (
          <Link to={`/room/${roomId}/admin`} className="btn-ghost">
            Управление
          </Link>
        )}
      </div>

      {showRules && (
        <div
          className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4"
          onClick={() => setShowRules(false)}
        >
          <div
            className="max-h-[80vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Регламент</h2>
              <button
                className="text-slate-400 hover:text-slate-600"
                onClick={() => setShowRules(false)}
                aria-label="Закрыть"
              >
                ✕
              </button>
            </div>
            <p className="whitespace-pre-line text-sm text-slate-700">{rulesText}</p>
          </div>
        </div>
      )}

      {archived && (
        <div className="rounded-lg bg-amber-100 px-4 py-2 text-sm text-amber-800">
          Соревнование в архиве — приём прогнозов и начисление очков закрыты. Таблица
          доступна только для просмотра.
        </div>
      )}

      <div className="flex gap-2 border-b">
        {([
          ["table", "Таблица"],
          ["predictions", "Прогнозы"],
          ["wc", "ЧМ-2026"],
        ] as const).map(([id, label]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`px-3 py-2 ${
              tab === id
                ? "border-b-2 border-brand font-semibold text-brand"
                : "text-slate-500"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "table" && (
        <section className="card">
          {lb.isLoading ? (
            <p className="text-slate-500">Загрузка…</p>
          ) : (
            <LeaderboardTable
              entries={lb.data || []}
              roomId={roomId!}
              started={started}
              isAdmin={isAdmin}
            />
          )}
        </section>
      )}

      {tab === "wc" && <WcStandings roomId={roomId!} />}

      {tab === "predictions" && (
        <div className="space-y-6">
          {/* Спецпрогноз доступен только до старта турнира. */}
          {!started && <SpecialPredictionCard roomId={roomId!} />}

          <section className="card">
            <h2 className="mb-3 text-lg font-semibold">Туры</h2>
            {days.isLoading ? (
              <p className="text-slate-500">Загрузка…</p>
            ) : !days.data?.length ? (
              <p className="text-slate-500">Матчи ещё не добавлены.</p>
            ) : (
              <div className="grid gap-2 sm:grid-cols-2">
                {days.data.map((d) => {
                  const st = dayStatus(d);
                  const tourStarted = isPast(d.first_kickoff_at);
                  const tourLive = tourStarted && d.finished_count < d.match_count;
                  return (
                    <Link
                      key={d.date}
                      to={`/room/${roomId}/tour/${d.date}`}
                      className={`flex items-center justify-between gap-2 rounded-lg border p-3 transition ${st.cls}`}
                    >
                      <span className="flex min-w-0 flex-col">
                        <span className="flex items-center gap-1.5 font-medium">
                          {formatDate(d.date)}
                          {d.multiplier != null && <MultiplierBadge value={d.multiplier} />}
                        </span>
                        <span className="text-xs text-slate-500">
                          {d.my_predictions_count}/{d.match_count} прогнозов
                        </span>
                        {st.label && (
                          <span className={`text-xs ${st.labelCls}`}>{st.label}</span>
                        )}
                      </span>
                      {/* Очки за тур: крупно; красная точка — тур ещё идёт. */}
                      {tourStarted && (
                        <span className="flex shrink-0 items-center gap-1.5">
                          {tourLive && (
                            <span
                              className="h-2 w-2 animate-pulse rounded-full bg-red-600"
                              title="Тур ещё идёт"
                            />
                          )}
                          <span className="text-2xl font-extrabold tabular-nums text-slate-700">
                            +{d.my_points}
                          </span>
                        </span>
                      )}
                    </Link>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
