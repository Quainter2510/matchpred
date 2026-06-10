import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/endpoints";
import LeaderboardTable from "../components/LeaderboardTable";
import SpecialPredictionCard from "./SpecialPredictionCard";
import { formatDate } from "../utils/dates";

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
          <LeaderboardTable entries={lb.data || []} />
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
            {days.data.map((d) => (
              <Link
                key={d.date}
                to={`/room/${roomId}/tour/${d.date}`}
                className="flex items-center justify-between rounded-lg border p-3 hover:bg-slate-50"
              >
                <span className="font-medium">{formatDate(d.date)}</span>
                <span className="text-sm text-slate-500">
                  {d.my_predictions_count}/{d.match_count} прогнозов
                </span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
