import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/endpoints";
import { teamLabel } from "../utils/countries";

export default function MatchPredictions() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const match = useQuery({
    queryKey: ["match", id],
    queryFn: () => api.match(id!),
    enabled: !!id,
  });
  const preds = useQuery({
    queryKey: ["match-preds", id],
    queryFn: () => api.matchPredictions(id!),
    enabled: !!id,
  });

  return (
    <div className="space-y-4">
      <button onClick={() => navigate(-1)} className="btn-ghost">
        ← Назад
      </button>
      {match.data && (
        <h1 className="text-xl font-bold">
          {teamLabel(match.data.home_team)} {match.data.home_score_ft ?? ""}
          {match.data.status === "finished" ? " : " : " — "}
          {match.data.away_score_ft ?? ""} {teamLabel(match.data.away_team)}
        </h1>
      )}
      <div className="card">
        {preds.isError ? (
          <p className="text-slate-500">Прогнозы скрыты до начала матча.</p>
        ) : preds.isLoading ? (
          <p className="text-slate-500">Загрузка…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-slate-500">
                <th className="py-2">Игрок</th>
                <th className="text-center">Прогноз</th>
                <th className="text-right">Очки</th>
              </tr>
            </thead>
            <tbody>
              {(preds.data || []).map((p) => (
                <tr key={p.user_id} className="border-b">
                  <td className="flex items-center gap-2 py-2">
                    {p.avatar_url ? (
                      <img src={p.avatar_url} className="h-6 w-6 rounded-full" />
                    ) : (
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-300 text-xs">
                        {p.nickname[0]?.toUpperCase()}
                      </div>
                    )}
                    {p.nickname}
                  </td>
                  <td className="text-center font-medium">
                    {p.predicted_home}:{p.predicted_away}
                  </td>
                  <td className="text-right">
                    {p.points_awarded != null ? (
                      <span
                        className={
                          p.is_exact ? "font-bold text-emerald-600" : ""
                        }
                      >
                        +{p.points_awarded}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
