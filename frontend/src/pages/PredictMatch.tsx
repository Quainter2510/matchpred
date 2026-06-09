import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/endpoints";
import ScoreInput from "../components/ScoreInput";
import Countdown from "../components/Countdown";
import TeamName from "../components/TeamName";
import { formatDate, formatTime, isPast } from "../utils/dates";
import { previewPoints } from "../utils/scoring";

export default function PredictMatch() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: match, isLoading } = useQuery({
    queryKey: ["match", id],
    queryFn: () => api.match(id!),
    enabled: !!id,
  });

  const [home, setHome] = useState<number | "">("");
  const [away, setAway] = useState<number | "">("");

  useEffect(() => {
    if (match?.my_prediction) {
      setHome(match.my_prediction.predicted_home);
      setAway(match.my_prediction.predicted_away);
    }
  }, [match]);

  const save = useMutation({
    mutationFn: () =>
      api.batchPredict([
        { match_id: id!, home: Number(home), away: Number(away) },
      ]),
    onSuccess: (res: any) => {
      const r = res.results?.[0];
      if (r && !r.accepted) {
        alert(r.reason === "deadline_passed" ? "Приём завершён" : "Отклонено");
      } else {
        qc.invalidateQueries({ queryKey: ["match", id] });
        navigate(-1);
      }
    },
  });

  if (isLoading || !match) return <p className="text-slate-500">Загрузка…</p>;

  const closed = isPast(match.kickoff_at);
  const valid = home !== "" && away !== "";

  return (
    <div className="mx-auto max-w-md space-y-4">
      <button onClick={() => navigate(-1)} className="btn-ghost">
        ← Назад
      </button>
      <div className="card space-y-4 text-center">
        <div className="text-sm text-slate-500">
          {formatDate(match.match_date)} · {formatTime(match.kickoff_at)} · {match.stage}
        </div>
        <div className="text-sm">
          Дедлайн: <Countdown to={match.kickoff_at} />
        </div>

        <div className="grid grid-cols-3 items-center gap-2">
          <TeamName team={match.home_team} flagSide="right" className="justify-end text-right font-semibold" />
          <div className="flex items-center justify-center gap-2">
            <ScoreInput value={home} onChange={setHome} disabled={closed} />
            <span>:</span>
            <ScoreInput value={away} onChange={setAway} disabled={closed} />
          </div>
          <TeamName team={match.away_team} className="justify-start text-left font-semibold" />
        </div>

        {closed ? (
          <p className="rounded bg-red-100 px-3 py-2 text-red-700">
            Приём прогнозов завершён
          </p>
        ) : (
          <button
            className="btn-primary w-full"
            disabled={!valid || save.isPending}
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
    </div>
  );
}
