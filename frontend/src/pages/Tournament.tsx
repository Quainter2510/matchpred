import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
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
            {days.data.map((d) => {
              const st = dayStatus(d);
              return (
                <Link
                  key={d.date}
                  to={`/tour/${d.date}`}
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
