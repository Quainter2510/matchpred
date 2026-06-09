import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/endpoints";
import LeaderboardTable from "../components/LeaderboardTable";
import SpecialPredictionCard from "./SpecialPredictionCard";
import { formatDate } from "../utils/dates";

export default function Tournament() {
  const lb = useQuery({ queryKey: ["leaderboard"], queryFn: api.leaderboard });
  const days = useQuery({ queryKey: ["days"], queryFn: api.matchDays });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Турнир</h1>

      <section className="card">
        <h2 className="mb-3 text-lg font-semibold">Таблица лидеров</h2>
        {lb.isLoading ? (
          <p className="text-slate-500">Загрузка…</p>
        ) : (
          <LeaderboardTable entries={lb.data || []} />
        )}
      </section>

      <SpecialPredictionCard />

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
                to={`/tour/${d.date}`}
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
