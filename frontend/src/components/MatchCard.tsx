import { Link } from "react-router-dom";
import { Match } from "../api/endpoints";
import { useAuth } from "../store/auth";
import { useViewAs } from "../store/viewAs";
import { formatTime, isPast } from "../utils/dates";
import { formatStage } from "../utils/stage";
import { classifyPrediction, HitKind } from "../utils/scoring";
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

// Категория попадания моего прогноза в сыгранном матче (null — рано судить).
function hitKind(match: Match): HitKind | null {
  const p = match.my_prediction;
  if (
    !p ||
    p.points_awarded == null ||
    match.status !== "finished" ||
    match.home_score_ft == null ||
    match.away_score_ft == null
  )
    return null;
  return classifyPrediction(
    p.predicted_home,
    p.predicted_away,
    match.home_score_ft,
    match.away_score_ft
  );
}

// Заливка карточки сыгранного матча по результату прогноза. `!` нужен, потому
// что .card задаёт bg/border позже utilities в index.css.
const CARD_TINT: Record<HitKind, string> = {
  exact: "!border-emerald-200 !bg-emerald-50/60",
  diff: "!border-sky-200 !bg-sky-50/60",
  outcome: "!border-amber-200 !bg-amber-50/60",
  miss: "!border-rose-200 !bg-rose-50/60",
};

const BADGE_TINT: Record<HitKind, string> = {
  exact: "bg-emerald-100 text-emerald-700",
  diff: "bg-sky-100 text-sky-700",
  outcome: "bg-amber-100 text-amber-800",
  miss: "bg-rose-100 text-rose-700",
};

export function LiveBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded bg-red-100 px-1.5 py-0.5 text-xs font-semibold text-red-600">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-600" />
      LIVE
    </span>
  );
}

export default function MatchCard({ match, roomId }: { match: Match; roomId: string }) {
  // Кнопка «Итоги» — только при включённом режиме суперадмина.
  const adminMode = useViewAs((s) => s.adminMode);
  const isSuper = useAuth((s) => s.isSuperadmin()) && adminMode;
  const started = isPast(match.kickoff_at);
  const finished = match.status === "finished";
  const live = match.status === "live";
  const hasScore = match.home_score_ft != null && match.away_score_ft != null;
  const p = match.my_prediction;
  const kind = hitKind(match);

  return (
    <div
      className={`card flex h-full flex-col gap-3 ${multiplierRing(match.points_multiplier)} ${
        kind ? CARD_TINT[kind] : ""
      }`}
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
            <span className="inline-flex items-center gap-1">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-600" />
              Идёт
            </span>
          )}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <div className="flex min-w-0 flex-1 justify-end">
          <TeamName team={match.home_team} flagSide="right" className="text-right font-medium" />
        </div>
        <div
          className={`shrink-0 px-1 text-center font-bold tabular-nums ${
            hasScore ? "text-2xl" : "text-lg text-slate-400"
          } ${live ? "text-red-600" : ""}`}
        >
          {hasScore ? `${match.home_score_ft}:${match.away_score_ft}` : "vs"}
        </div>
        <div className="flex min-w-0 flex-1 justify-start">
          <TeamName team={match.away_team} className="text-left font-medium" />
        </div>
      </div>

      {p && (
        <div className="flex items-center justify-center gap-2 text-slate-600">
          <span className="text-sm">Мой прогноз:</span>
          <b className="text-xl tabular-nums">
            {p.predicted_home}:{p.predicted_away}
          </b>
          {p.points_awarded != null && (
            <span
              className={`rounded px-2 py-0.5 text-lg font-bold tabular-nums ${
                kind ? BADGE_TINT[kind] : "bg-emerald-100 text-emerald-700"
              }`}
            >
              +{p.points_awarded}
            </span>
          )}
        </div>
      )}

      <div className="mt-auto flex gap-2">
        {!started ? (
          <>
            <Link to={`/room/${roomId}/match/${match.id}/predict`} className="btn-primary flex-1">
              {p ? "Изменить прогноз" : "Сделать прогноз"}
            </Link>
            {/* Суперадмин видит прогнозы всех и до начала матча. */}
            {isSuper && (
              <Link
                to={`/room/${roomId}/match/${match.id}/predictions`}
                className="btn-ghost"
                title="Прогнозы всех участников (видно только админам)"
              >
                Итоги
              </Link>
            )}
          </>
        ) : (
          <Link to={`/room/${roomId}/match/${match.id}/predictions`} className="btn-ghost flex-1">
            Прогнозы участников
          </Link>
        )}
      </div>
    </div>
  );
}
