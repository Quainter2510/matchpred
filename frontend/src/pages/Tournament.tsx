import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api, MatchDay } from "../api/endpoints";
import LeaderboardTable from "../components/LeaderboardTable";
import SpecialPredictionCard from "./SpecialPredictionCard";
import { formatDate, isPast } from "../utils/dates";

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
  const msToStart = new Date(d.first_kickoff_at).getTime() - Date.now();
  if (msToStart <= 2 * DAY_MS)
    return {
      cls: "border-amber-300 bg-amber-50 hover:bg-amber-100",
      label: "Скоро дедлайн",
      labelCls: "text-amber-700",
    };
  return { cls: "hover:bg-slate-50", label: "", labelCls: "" };
}

export default function Tournament() {
  const { roomId } = useParams<{ roomId: string }>();
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

  const isRoomAdmin = room.data?.my_role === "admin";
  const archived = room.data && !room.data.is_active;
  const s = room.data?.scoring;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/" className="text-sm text-slate-500 hover:underline">
            ← Все комнаты
          </Link>
          <h1 className="text-2xl font-bold">
            {room.data?.name || "Комната"}
            {archived && <span className="ml-2 text-sm text-slate-400">(архив)</span>}
          </h1>
          {s && (
            <p className="text-xs text-slate-500">
              Очки: точный {s.points_exact} · разница {s.points_diff} · исход{" "}
              {s.points_outcome} · чемпион {s.points_champion} · бомбардир{" "}
              {s.points_scorer}
            </p>
          )}
        </div>
        {isRoomAdmin && (
          <Link to={`/room/${roomId}/admin`} className="btn-ghost">
            Управление
          </Link>
        )}
      </div>

      {archived && (
        <div className="rounded-lg bg-amber-100 px-4 py-2 text-sm text-amber-800">
          Комната в архиве — приём прогнозов и начисление очков закрыты. Таблица
          доступна только для просмотра.
        </div>
      )}

      <section className="card">
        <h2 className="mb-3 text-lg font-semibold">Таблица лидеров</h2>
        {lb.isLoading ? (
          <p className="text-slate-500">Загрузка…</p>
        ) : (
          <LeaderboardTable entries={lb.data || []} roomId={roomId!} />
        )}
      </section>

      <SpecialPredictionCard roomId={roomId!} />

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
              return (
                <Link
                  key={d.date}
                  to={`/room/${roomId}/tour/${d.date}`}
                  className={`flex items-center justify-between rounded-lg border p-3 transition ${st.cls}`}
                >
                  <span className="flex flex-col">
                    <span className="font-medium">{formatDate(d.date)}</span>
                    {st.label && (
                      <span className={`text-xs ${st.labelCls}`}>{st.label}</span>
                    )}
                  </span>
                  <span className="text-sm text-slate-500">
                    {d.my_predictions_count}/{d.match_count} прогнозов
                  </span>
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
