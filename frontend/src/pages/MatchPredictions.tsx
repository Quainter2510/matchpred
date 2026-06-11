import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, Match, PlayerPrediction } from "../api/endpoints";
import { LiveBadge } from "../components/MatchCard";
import MultiplierBadge from "../components/MultiplierBadge";
import TeamName from "../components/TeamName";
import { classifyPrediction, HIT_BG } from "../utils/scoring";

// Очки начислены → сортируем по убыванию; сделавшие прогноз выше тех, кто
// без прогноза (у них прочерки); внутри — по нику.
function byPoints(a: PlayerPrediction, b: PlayerPrediction): number {
  const ap = a.points_awarded ?? -1;
  const bp = b.points_awarded ?? -1;
  if (bp !== ap) return bp - ap;
  const aHas = a.predicted_home != null;
  const bHas = b.predicted_home != null;
  if (aHas !== bHas) return aHas ? -1 : 1;
  if (!!b.is_exact !== !!a.is_exact) return b.is_exact ? 1 : -1;
  return a.nickname.localeCompare(b.nickname, "ru");
}

// Единая цветовая схема: точный — зелёный, разница — синий, исход — янтарный,
// промах — красный. Категория считается по счёту, а не по очкам, поэтому
// не зависит от правил комнаты и коэффициента матча.
function rowTint(p: PlayerPrediction, m: Match | undefined): string {
  if (
    p.predicted_home == null ||
    p.predicted_away == null ||
    p.points_awarded == null ||
    !m ||
    m.status !== "finished" ||
    m.home_score_ft == null ||
    m.away_score_ft == null
  )
    return "";
  return HIT_BG[
    classifyPrediction(
      p.predicted_home,
      p.predicted_away,
      m.home_score_ft,
      m.away_score_ft
    )
  ];
}

export default function MatchPredictions() {
  const { roomId, id } = useParams<{ roomId: string; id: string }>();
  const navigate = useNavigate();
  // Раз в минуту подтягиваем live-счёт и очки, начисленные после завершения.
  const match = useQuery({
    queryKey: ["match", roomId, id],
    queryFn: () => api.match(roomId!, id!),
    enabled: !!roomId && !!id,
    refetchInterval: 60_000,
  });
  const preds = useQuery({
    queryKey: ["match-preds", roomId, id],
    queryFn: () => api.matchPredictions(roomId!, id!),
    enabled: !!roomId && !!id,
    refetchInterval: 60_000,
  });

  return (
    <div className="space-y-4">
      <button onClick={() => navigate(-1)} className="btn-ghost">
        ← Назад
      </button>
      {match.data && (
        <h1 className="flex flex-wrap items-center gap-2 text-xl font-bold">
          <TeamName team={match.data.home_team} />
          <span className={match.data.status === "live" ? "text-red-600" : ""}>
            {match.data.home_score_ft ?? ""}
            {match.data.home_score_ft != null && match.data.away_score_ft != null
              ? " : "
              : " — "}
            {match.data.away_score_ft ?? ""}
          </span>
          <TeamName team={match.data.away_team} />
          {match.data.status === "live" && <LiveBadge />}
          <MultiplierBadge value={match.data.points_multiplier} large />
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
              {[...(preds.data || [])].sort(byPoints).map((p) => (
                <tr key={p.user_id} className={`border-b ${rowTint(p, match.data)}`}>
                  <td className="flex items-center gap-2 py-2">
                    {p.avatar_url ? (
                      <img src={p.avatar_url} className="h-6 w-6 rounded-full" />
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
                  <td className="text-center font-medium">
                    {p.predicted_home != null && p.predicted_away != null ? (
                      `${p.predicted_home}:${p.predicted_away}`
                    ) : (
                      <span className="text-slate-300">—</span>
                    )}
                  </td>
                  <td className="text-right">
                    {p.points_awarded != null ? (
                      <span className={p.is_exact ? "font-bold text-emerald-600" : ""}>
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
