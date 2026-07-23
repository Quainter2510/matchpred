import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, MatchDay, RoomScoring, StandingsMatch } from "../api/endpoints";
import LeaderboardTable from "../components/LeaderboardTable";
import MultiplierBadge from "../components/MultiplierBadge";
import WcStandings from "../components/WcStandings";
import Flag from "../components/Flag";
import SpecialPredictionCard from "./SpecialPredictionCard";
import { useAuth } from "../store/auth";
import { useViewAs } from "../store/viewAs";
import { findCountry } from "../utils/countries";
import { formatDate, isPast, nowMs } from "../utils/dates";

// Ссылки на все начавшиеся матчи (флаги + счёт) над вкладками: самый свежий
// слева, дальше листается вправо. На телефоне — свайпом, в браузере — кнопками
// по краям. Скроллбар скрыт. Данные из standings (общий кэш с вкладкой ЧМ).
function RecentResults({ roomId }: { roomId: string }) {
  const { data } = useQuery({
    queryKey: ["standings", roomId],
    queryFn: () => api.standings(roomId),
    refetchInterval: 5 * 60_000,
  });
  const scroller = useRef<HTMLDivElement>(null);
  const [edges, setEdges] = useState({ start: true, end: true });

  const now = nowMs();
  const recent: StandingsMatch[] = data
    ? [
        ...data.groups.flatMap((g) => g.matches),
        ...data.playoff.flatMap((p) => p.matches),
      ]
        .filter((m) => new Date(m.kickoff_at).getTime() <= now)
        .sort(
          (a, b) =>
            new Date(b.kickoff_at).getTime() - new Date(a.kickoff_at).getTime()
        )
    : [];

  const updateEdges = () => {
    const el = scroller.current;
    if (!el) return;
    setEdges({
      start: el.scrollLeft <= 1,
      end: el.scrollLeft + el.clientWidth >= el.scrollWidth - 1,
    });
  };
  useEffect(updateEdges, [recent.length]);

  if (!recent.length) return null;

  const scrollByPage = (dir: number) => {
    const el = scroller.current;
    if (el) el.scrollBy({ left: dir * el.clientWidth * 0.8, behavior: "smooth" });
  };

  const arrowBtn =
    "absolute top-1/2 z-10 hidden h-7 w-7 -translate-y-1/2 items-center justify-center " +
    "rounded-full border border-slate-200 bg-white text-slate-600 shadow-sm hover:bg-slate-50 md:flex";

  return (
    <div className="relative">
      {!edges.start && (
        <button
          type="button"
          aria-label="Предыдущие"
          onClick={() => scrollByPage(-1)}
          className={`${arrowBtn} left-0`}
        >
          ‹
        </button>
      )}
      <div
        ref={scroller}
        onScroll={updateEdges}
        className="flex items-center gap-2 overflow-x-auto [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {recent.map((m) => {
          const hc = findCountry(m.home_team);
          const ac = findCountry(m.away_team);
          const live = m.status === "live";
          const score =
            m.home_score != null && m.away_score != null
              ? `${m.home_score}:${m.away_score}`
              : "–";
          return (
            <Link
              key={m.id}
              to={`/room/${roomId}/match/${m.id}/predictions`}
              title={`${m.home_team} ${score} ${m.away_team}`}
              className="inline-flex shrink-0 items-center gap-1 rounded-full border border-slate-200 px-2 py-0.5 text-xs hover:bg-slate-50"
            >
              {hc ? <Flag code={hc.code} title={m.home_team} /> : null}
              <span
                className={`font-semibold tabular-nums ${live ? "text-red-600" : ""}`}
              >
                {score}
              </span>
              {ac ? <Flag code={ac.code} title={m.away_team} /> : null}
            </Link>
          );
        })}
      </div>
      {!edges.end && (
        <button
          type="button"
          aria-label="Следующие"
          onClick={() => scrollByPage(1)}
          className={`${arrowBtn} right-0`}
        >
          ›
        </button>
      )}
    </div>
  );
}

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
      cls: "border-emerald-200 bg-emerald-50/60 hover:bg-emerald-50",
      label: "Прогноз готов",
      labelCls: "text-emerald-700",
    };
  if (isPast(d.first_kickoff_at))
    return {
      cls: "border-rose-200 bg-rose-50/60 hover:bg-rose-50",
      label: "Прогноз пропущен",
      labelCls: "text-rose-700",
    };
  const msToStart = new Date(d.first_kickoff_at).getTime() - nowMs();
  if (msToStart <= 2 * DAY_MS)
    return {
      cls: "border-amber-200 bg-amber-50/60 hover:bg-amber-50",
      label: "Скоро дедлайн",
      labelCls: "text-amber-700",
    };
  return { cls: "hover:bg-slate-50", label: "", labelCls: "" };
}

// Стандартный регламент, когда админ не заполнил свой текст.
function defaultRules(
  s: RoomScoring | null | undefined,
  specialKind?: string
): string {
  if (!s) return "Регламент не заполнен.";
  const lines = [
    "Начисление очков:",
    `• точный счёт — ${s.points_exact}`,
    `• разница мячей — ${s.points_diff}`,
    `• исход (победитель/ничья) — ${s.points_outcome}`,
  ];
  if (specialKind === "leader") {
    lines.push(`• лидер лиги на финальный момент — ${s.points_champion}`);
  } else if (specialKind === "stage_or_champion") {
    lines.push(`• победитель / чемпион — ${s.points_champion}`);
  } else if (specialKind === "wc" || specialKind === undefined) {
    lines.push(`• чемпион турнира — ${s.points_champion}`);
    lines.push(`• лучший бомбардир — ${s.points_scorer}`);
  }
  return lines.join("\n");
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
  // Суперадмин по умолчанию — в режиме игрока: админ-кнопки появляются только
  // при включённом «режиме суперадмина» (бэкенд в режиме игрока всё равно
  // ответит 403 на управление комнатой). Обычных админов комнат это не
  // касается — у них прав суперадмина нет.
  const adminMode = useViewAs((s) => s.adminMode);
  const asPlayer = me?.system_role === "superadmin" && !adminMode;
  const isRoomAdmin = room.data?.my_role === "admin" && !asPlayer;
  const isAdmin = (me?.system_role === "superadmin" && !asPlayer) || isRoomAdmin;
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

  // Свайп вкладок влево/вправо на телефоне.
  const TAB_ORDER = ["table", "predictions", "wc"] as const;
  const touchStart = useRef<{ x: number; y: number } | null>(null);
  const onTouchStart = (e: React.TouchEvent) => {
    const t = e.touches[0];
    touchStart.current = { x: t.clientX, y: t.clientY };
  };
  const onTouchEnd = (e: React.TouchEvent) => {
    const start = touchStart.current;
    touchStart.current = null;
    if (!start) return;
    const t = e.changedTouches[0];
    const dx = t.clientX - start.x;
    const dy = t.clientY - start.y;
    // Только явный горизонтальный жест — вертикальный скролл не трогаем.
    if (Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
    const idx = TAB_ORDER.indexOf(tab);
    const next = dx < 0 ? idx + 1 : idx - 1;
    if (next >= 0 && next < TAB_ORDER.length) setTab(TAB_ORDER[next]);
  };

  const [showRules, setShowRules] = useState(false);
  const rulesText =
    room.data?.rules_text ||
    defaultRules(room.data?.scoring, room.data?.special_kind);

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

      <RecentResults roomId={roomId!} />

      <div className="flex gap-2 border-b">
        {([
          ["table", "Таблица"],
          ["predictions", "Прогнозы"],
          [
            "wc",
            room.data?.tournament_type === "world_cup"
              ? "ЧМ-2026"
              : room.data?.tournament_type === "custom"
                ? "Матчи"
                : "Положение",
          ],
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

      <div onTouchStart={onTouchStart} onTouchEnd={onTouchEnd} className="space-y-6">
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
              specialKind={room.data?.special_kind}
            />
          )}
        </section>
      )}

      {tab === "wc" && (
        <WcStandings
          roomId={roomId!}
          tournamentType={room.data?.tournament_type}
        />
      )}

      {tab === "predictions" && (
        <div className="space-y-6">
          {/* Спецпрогноз доступен только до старта турнира. */}
          {!started && (
            <SpecialPredictionCard
              roomId={roomId!}
              specialKind={room.data?.special_kind}
            />
          )}

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
                  // Пропущенный (не полностью заполненный) тур — очки красным.
                  const missed =
                    tourStarted && d.my_predictions_count < d.match_count;
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
                        {d.members_total != null && d.members_filled != null && (
                          <span
                            className="text-xs text-slate-500"
                            title="Сколько участников дали прогноз на все матчи дня"
                          >
                            заполнили: {d.members_filled}/{d.members_total}
                          </span>
                        )}
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
                          <span
                            className={`text-2xl font-extrabold tabular-nums ${
                              missed ? "text-rose-600" : "text-slate-700"
                            }`}
                          >
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
    </div>
  );
}
