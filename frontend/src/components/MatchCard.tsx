import { Link } from "react-router-dom";
import { Match } from "../api/endpoints";
import { formatTime, isPast } from "../utils/dates";
import { formatStage } from "../utils/stage";
import Countdown from "./Countdown";
import MultiplierBadge from "./MultiplierBadge";
import TeamName from "./TeamName";

// Подсветка всей плашки бонусного матча (×2/×3) и аннулированного (×0).
function multiplierRing(m: number): string {
  if (m === 0) return "ring-2 ring-slate-400 opacity-75";
  if (m === 2) return "ring-2 ring-amber-400";
  if (m === 3) return "ring-2 ring-fuchsia-500";
  return "";
}

export function LiveBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded bg-red-100 px-1.5 py-0.5 text-xs font-semibold text-red-600">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-600" />
      LIVE
    </span>
  );
}

export default function MatchCard({ match, roomId }: { match: Match; roomId: string }) {
  const started = isPast(match.kickoff_at);
  const finished = match.status === "finished";
  const live = match.status === "live";
  const hasScore = match.home_score_ft != null && match.away_score_ft != null;
  const p = match.my_prediction;

  return (
    <div
      className={`card flex h-full flex-col gap-3 ${multiplierRing(match.points_multiplier)}`}
    >
      <div className="flex items-center justify-between gap-2 text-xs text-slate-500">
        <span className="flex min-w-0 items-center gap-1.5 truncate">
          <MultiplierBadge value={match.points_multiplier} />
          <span className="truncate">
            {formatTime(match.kickoff_at)} · {formatStage(match.stage, match.group_name)}
          </span>
        </span>
        <span className="shrink-0">
          {live ? (
            <LiveBadge />
          ) : !started ? (
            <Countdown to={match.kickoff_at} />
          ) : finished ? (
            "Завершён"
          ) : (
            "Идёт/закрыт"
          )}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <div className="flex min-w-0 flex-1 justify-end">
          <TeamName team={match.home_team} flagSide="right" className="text-right font-medium" />
        </div>
        <div
          className={`shrink-0 px-1 text-center text-lg font-bold ${live ? "text-red-600" : ""}`}
        >
          {hasScore ? `${match.home_score_ft}:${match.away_score_ft}` : "vs"}
        </div>
        <div className="flex min-w-0 flex-1 justify-start">
          <TeamName team={match.away_team} className="text-left font-medium" />
        </div>
      </div>

      {p && (
        <div className="text-center text-sm text-slate-600">
          Мой прогноз: <b>{p.predicted_home}:{p.predicted_away}</b>
          {p.points_awarded != null && (
            <span className="ml-2 rounded bg-emerald-100 px-2 py-0.5 text-emerald-700">
              +{p.points_awarded}
            </span>
          )}
        </div>
      )}

      <div className="mt-auto flex gap-2">
        {!started ? (
          <Link to={`/room/${roomId}/match/${match.id}/predict`} className="btn-primary flex-1">
            {p ? "Изменить прогноз" : "Сделать прогноз"}
          </Link>
        ) : (
          <Link to={`/room/${roomId}/match/${match.id}/predictions`} className="btn-ghost flex-1">
            Прогнозы участников
          </Link>
        )}
      </div>
    </div>
  );
}
