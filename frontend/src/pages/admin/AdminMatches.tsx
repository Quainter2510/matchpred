import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, Match } from "../../api/endpoints";
import { formatDate, formatTime } from "../../utils/dates";

function ResultRow({ match }: { match: Match }) {
  const qc = useQueryClient();
  const [h, setH] = useState<string>(match.home_score_ft?.toString() ?? "");
  const [a, setA] = useState<string>(match.away_score_ft?.toString() ?? "");
  const save = useMutation({
    mutationFn: () => api.setResult(match.id, Number(h), Number(a)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-matches"] });
      qc.invalidateQueries({ queryKey: ["leaderboard"] });
    },
  });
  return (
    <tr className="border-b">
      <td className="py-2 text-xs text-slate-500">
        {formatDate(match.match_date)} {formatTime(match.kickoff_at)}
      </td>
      <td>{match.home_team} — {match.away_team}</td>
      <td>
        <input className="w-12 rounded border px-1 text-center" value={h} onChange={(e) => setH(e.target.value)} />
        :
        <input className="w-12 rounded border px-1 text-center" value={a} onChange={(e) => setA(e.target.value)} />
      </td>
      <td>
        <button
          className="btn-primary px-2 py-1 text-sm"
          disabled={h === "" || a === "" || save.isPending}
          onClick={() => save.mutate()}
        >
          {match.status === "finished" ? "Обновить" : "Ввести"}
        </button>
      </td>
    </tr>
  );
}

export default function AdminMatches() {
  const qc = useQueryClient();
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const matches = useQuery({
    queryKey: ["admin-matches", date],
    queryFn: () => api.matchesByDate(date),
  });
  const sync = useMutation({
    mutationFn: api.sync,
    onSuccess: (r) => {
      alert(`Синхронизировано. ${JSON.stringify(r)}`);
      qc.invalidateQueries({ queryKey: ["admin-matches"] });
    },
    onError: () => alert("Ошибка синхронизации (проверьте API-ключ)"),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="date"
          className="input w-auto"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
        <button
          className="btn-ghost"
          onClick={() => sync.mutate()}
          disabled={sync.isPending}
        >
          {sync.isPending ? "Синхронизация…" : "Синхронизировать с API-Football"}
        </button>
      </div>
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-slate-500">
              <th className="py-2">Когда</th>
              <th>Матч</th>
              <th>Счёт (90 мин)</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {(matches.data || []).map((m) => (
              <ResultRow key={m.id} match={m} />
            ))}
          </tbody>
        </table>
        {!matches.data?.length && (
          <p className="text-slate-500">Нет матчей на эту дату.</p>
        )}
      </div>
    </div>
  );
}
