import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/endpoints";
import MatchCard from "../components/MatchCard";
import { formatDate } from "../utils/dates";

export default function Tour() {
  const { date } = useParams<{ date: string }>();
  const { data, isLoading } = useQuery({
    queryKey: ["matches", date],
    queryFn: () => api.matchesByDate(date!),
    enabled: !!date,
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link to="/" className="btn-ghost">
          ← Назад
        </Link>
        <h1 className="text-2xl font-bold">{date && formatDate(date)}</h1>
      </div>
      {isLoading ? (
        <p className="text-slate-500">Загрузка…</p>
      ) : !data?.length ? (
        <p className="text-slate-500">Нет матчей.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {data.map((m) => (
            <MatchCard key={m.id} match={m} />
          ))}
        </div>
      )}
    </div>
  );
}
