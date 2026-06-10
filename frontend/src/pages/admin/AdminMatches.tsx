import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, Match } from "../../api/endpoints";
import { formatDate, formatTime } from "../../utils/dates";
import MultiplierBadge from "../../components/MultiplierBadge";
import TeamName from "../../components/TeamName";

const MULTIPLIERS = [0, 1, 2, 3];

function ResultRow({ match }: { match: Match }) {
  const qc = useQueryClient();
  const [h, setH] = useState<string>(match.home_score_ft?.toString() ?? "");
  const [a, setA] = useState<string>(match.away_score_ft?.toString() ?? "");
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["admin-matches"] });
    qc.invalidateQueries({ queryKey: ["leaderboard"] });
  };
  const save = useMutation({
    mutationFn: () => api.setResult(match.id, Number(h), Number(a)),
    onSuccess: invalidate,
  });
  const mult = useMutation({
    mutationFn: (m: number) => api.setMatchMultiplier(match.id, m),
    onSuccess: invalidate,
    onError: (e: any) => alert(e.response?.data?.detail || "Ошибка"),
  });
  return (
    <tr className="border-b">
      <td className="py-2 text-xs text-slate-500">
        {formatDate(match.match_date)} {formatTime(match.kickoff_at)}
      </td>
      <td>
        <span className="inline-flex flex-wrap items-center gap-1.5">
          <TeamName team={match.home_team} />
          <span className="text-slate-400">—</span>
          <TeamName team={match.away_team} />
          <MultiplierBadge value={match.points_multiplier} />
        </span>
      </td>
      <td>
        <input className="w-12 rounded border px-1 text-center" value={h} onChange={(e) => setH(e.target.value)} />
        :
        <input className="w-12 rounded border px-1 text-center" value={a} onChange={(e) => setA(e.target.value)} />
      </td>
      <td>
        <select
          className="rounded border px-1 py-1 text-sm"
          title="Бонусный коэффициент матча"
          value={match.points_multiplier}
          disabled={mult.isPending}
          onChange={(e) => mult.mutate(Number(e.target.value))}
        >
          {MULTIPLIERS.map((m) => (
            <option key={m} value={m}>
              ×{m}
            </option>
          ))}
        </select>
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
  const [tourMult, setTourMult] = useState(1);
  const matches = useQuery({
    queryKey: ["admin-matches", date],
    queryFn: () => api.adminMatchesByDate(date),
  });
  const sync = useMutation({
    mutationFn: api.sync,
    onSuccess: (r) => {
      alert(`Синхронизировано. ${JSON.stringify(r)}`);
      qc.invalidateQueries({ queryKey: ["admin-matches"] });
    },
    onError: () => alert("Ошибка синхронизации (проверьте API-ключ)"),
  });
  const tour = useMutation({
    mutationFn: () => api.setTourMultiplier(date, tourMult),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-matches"] });
      qc.invalidateQueries({ queryKey: ["leaderboard"] });
    },
    onError: (e: any) => alert(e.response?.data?.detail || "Ошибка"),
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
        <span className="ml-auto flex items-center gap-2 text-sm">
          Коэффициент тура:
          <select
            className="rounded border px-1 py-1"
            value={tourMult}
            onChange={(e) => setTourMult(Number(e.target.value))}
          >
            {MULTIPLIERS.map((m) => (
              <option key={m} value={m}>
                ×{m}
              </option>
            ))}
          </select>
          <button
            className="btn-ghost"
            disabled={tour.isPending || !matches.data?.length}
            onClick={() => {
              if (
                confirm(
                  `Установить коэффициент ×${tourMult} на все матчи ${formatDate(date)}?` +
                    (tourMult === 0 ? "\n\nВНИМАНИЕ: очки за тур будут обнулены!" : "")
                )
              )
                tour.mutate();
            }}
          >
            {tour.isPending ? "Применение…" : "Применить к туру"}
          </button>
        </span>
      </div>
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-slate-500">
              <th className="py-2">Когда</th>
              <th>Матч</th>
              <th>Счёт (90 мин)</th>
              <th>Кэф.</th>
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
