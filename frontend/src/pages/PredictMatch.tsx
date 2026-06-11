import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/endpoints";
import ScoreStepper from "../components/ScoreStepper";
import Countdown from "../components/Countdown";
import MultiplierBadge from "../components/MultiplierBadge";
import TeamForm from "../components/TeamForm";
import TeamName from "../components/TeamName";
import { formatDate, formatTime, isPast } from "../utils/dates";
import { formatStage } from "../utils/stage";

export default function PredictMatch() {
  const { roomId, id } = useParams<{ roomId: string; id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: match, isLoading } = useQuery({
    queryKey: ["match", roomId, id],
    queryFn: () => api.match(roomId!, id!),
    enabled: !!roomId && !!id,
  });
  // Форма команд: последние сыгранные матчи 2026 года (все турниры + ЧМ).
  const form = useQuery({
    queryKey: ["match-form", roomId, id],
    queryFn: () => api.matchForm(roomId!, id!),
    enabled: !!roomId && !!id,
  });

  // Изначально 0:0; если прогноз уже есть — подставляем его.
  const [home, setHome] = useState(0);
  const [away, setAway] = useState(0);

  useEffect(() => {
    if (match?.my_prediction) {
      setHome(match.my_prediction.predicted_home);
      setAway(match.my_prediction.predicted_away);
    }
  }, [match]);

  const save = useMutation({
    mutationFn: () => api.batchPredict(roomId!, [{ match_id: id!, home, away }]),
    onSuccess: (res: any) => {
      const r = res.results?.[0];
      if (r && !r.accepted) {
        alert(r.reason === "deadline_passed" ? "Приём завершён" : "Отклонено");
      } else {
        qc.invalidateQueries({ queryKey: ["match", roomId, id] });
        navigate(-1);
      }
    },
  });

  if (isLoading || !match) return <p className="text-slate-500">Загрузка…</p>;

  const closed = isPast(match.kickoff_at);

  return (
    <div className="mx-auto max-w-md space-y-4">
      <button onClick={() => navigate(-1)} className="btn-ghost">
        ← Назад
      </button>
      <div className="card space-y-4">
        <div className="text-center text-sm text-slate-500">
          {formatDate(match.match_date)} · {formatTime(match.kickoff_at)} · {formatStage(match.stage, match.group_name)}
        </div>
        <div className="text-center text-sm">
          Дедлайн: <Countdown to={match.kickoff_at} />
        </div>

        {match.points_multiplier !== 1 && (
          <div
            className={`flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium ${
              match.points_multiplier === 0
                ? "bg-slate-100 text-slate-600"
                : match.points_multiplier === 2
                  ? "bg-amber-100 text-amber-800"
                  : "bg-fuchsia-100 text-fuchsia-800"
            }`}
          >
            <MultiplierBadge value={match.points_multiplier} large />
            {match.points_multiplier === 0
              ? "Очки за этот матч не начисляются"
              : `Бонусный матч — очки умножаются на ${match.points_multiplier}`}
          </div>
        )}

        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 p-3">
            <TeamName
              team={match.home_team}
              className="min-w-0 flex-1 text-base font-semibold"
            />
            <ScoreStepper
              value={home}
              onChange={setHome}
              disabled={closed}
              label={match.home_team}
            />
          </div>
          <div className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 p-3">
            <TeamName
              team={match.away_team}
              className="min-w-0 flex-1 text-base font-semibold"
            />
            <ScoreStepper
              value={away}
              onChange={setAway}
              disabled={closed}
              label={match.away_team}
            />
          </div>
        </div>

        {closed ? (
          <p className="rounded bg-red-100 px-3 py-2 text-center text-red-700">
            Приём прогнозов завершён
          </p>
        ) : (
          <button
            className="btn-primary w-full"
            disabled={save.isPending}
            onClick={() => save.mutate()}
          >
            {save.isPending ? "Сохранение…" : "Сохранить прогноз"}
          </button>
        )}
        <p className="text-xs text-slate-400">
          Прогноз только на основное время (90 мин). Точный счёт — 5, разница — 2,
          исход — 1.
        </p>
      </div>

      {form.data && (form.data.home.length > 0 || form.data.away.length > 0) && (
        <div className="card space-y-4">
          <h2 className="text-sm font-semibold text-slate-500">
            Последние матчи в 2026 году
          </h2>
          <TeamForm team={form.data.home_team} matches={form.data.home} />
          <TeamForm team={form.data.away_team} matches={form.data.away} />
        </div>
      )}
    </div>
  );
}
