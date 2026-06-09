import { Link } from "react-router-dom";
import { Match } from "../api/endpoints";
import { formatTime, isPast } from "../utils/dates";
import Countdown from "./Countdown";
import TeamName from "./TeamName";

export default function MatchCard({ match }: { match: Match }) {
  const started = isPast(match.kickoff_at);
  const finished = match.status === "finished";
  const p = match.my_prediction;

  return (
    <div className="card flex flex-col gap-2">
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>{formatTime(match.kickoff_at)} · {match.stage}</span>
        {!started ? <Countdown to={match.kickoff_at} /> : <span>{finished ? "Завершён" : "Идёт/закрыт"}</span>}
      </div>
      <div className="grid grid-cols-3 items-center gap-2">
        <TeamName team={match.home_team} flagSide="right" className="justify-end text-right font-medium" />
        <div className="text-center text-xl font-bold">
          {finished
            ? `${match.home_score_ft} : ${match.away_score_ft}`
            : "vs"}
        </div>
        <TeamName team={match.away_team} className="justify-start text-left font-medium" />
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

      <div className="flex gap-2">
        {!started ? (
          <Link to={`/match/${match.id}/predict`} className="btn-primary flex-1">
            {p ? "Изменить прогноз" : "Сделать прогноз"}
          </Link>
        ) : (
          <Link to={`/match/${match.id}/predictions`} className="btn-ghost flex-1">
            Прогнозы участников
          </Link>
        )}
      </div>
    </div>
  );
}
