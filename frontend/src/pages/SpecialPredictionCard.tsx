import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/endpoints";
import PlayerSearch from "../components/PlayerSearch";
import CountrySelect from "../components/CountrySelect";
import TeamName from "../components/TeamName";

export default function SpecialPredictionCard({ roomId }: { roomId: string }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["special", roomId],
    queryFn: () => api.mySpecial(roomId),
  });

  const [champion, setChampion] = useState("");
  const [scorer, setScorer] = useState<{ id: number | null; name: string | null }>({
    id: null,
    name: null,
  });

  useEffect(() => {
    if (data) {
      setChampion(data.champion_team || "");
      setScorer({ id: data.top_scorer_api_id, name: data.top_scorer_name });
    }
  }, [data]);

  const save = useMutation({
    mutationFn: () =>
      api.updateSpecial(roomId, {
        champion_team: champion || null,
        top_scorer_name: scorer.name,
        top_scorer_api_id: scorer.id,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["special", roomId] }),
  });

  if (isLoading) return null;
  const locked = data?.locked;

  // Поле подсвечивается зелёным, когда текущее значение совпадает с сохранённым
  // на сервере (нет несохранённых правок).
  const championSaved = !!data?.champion_team && champion === data.champion_team;
  const scorerSaved =
    !!data?.top_scorer_api_id && scorer.id === data.top_scorer_api_id;

  return (
    <section className="card space-y-3">
      <h2 className="text-lg font-semibold">Спецпрогнозы</h2>
      {locked && (
        <p className="rounded bg-amber-100 px-3 py-2 text-sm text-amber-800">
          Приём спецпрогнозов завершён.
          {data?.champion_points != null && ` Чемпион: +${data.champion_points}.`}
          {data?.scorer_points != null && ` Бомбардир: +${data.scorer_points}.`}
        </p>
      )}
      <div>
        <label className="text-sm text-slate-600">Чемпион турнира</label>
        {locked ? (
          <div className="input flex items-center bg-slate-50">
            {champion ? <TeamName team={champion} /> : <span className="text-slate-400">—</span>}
          </div>
        ) : (
          <CountrySelect value={champion} onChange={setChampion} highlight={championSaved} />
        )}
      </div>
      <div>
        <label className="text-sm text-slate-600">Лучший бомбардир</label>
        <PlayerSearch
          value={scorer}
          disabled={locked}
          onSelect={(id, name) => setScorer({ id, name })}
          highlight={scorerSaved}
        />
      </div>
      {!locked && (
        <button
          className="btn-primary"
          onClick={() => save.mutate()}
          disabled={save.isPending}
        >
          {save.isPending ? "Сохранение…" : "Сохранить спецпрогноз"}
        </button>
      )}
    </section>
  );
}
