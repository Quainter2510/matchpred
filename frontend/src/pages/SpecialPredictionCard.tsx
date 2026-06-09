import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/endpoints";
import PlayerSearch from "../components/PlayerSearch";

export default function SpecialPredictionCard() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["special"],
    queryFn: api.mySpecial,
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
      api.updateSpecial({
        champion_team: champion || null,
        top_scorer_name: scorer.name,
        top_scorer_api_id: scorer.id,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["special"] }),
  });

  if (isLoading) return null;
  const locked = data?.locked;

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
        <input
          className="input"
          placeholder="Например: Бразилия"
          value={champion}
          disabled={locked}
          onChange={(e) => setChampion(e.target.value)}
        />
      </div>
      <div>
        <label className="text-sm text-slate-600">Лучший бомбардир</label>
        <PlayerSearch
          value={scorer}
          disabled={locked}
          onSelect={(id, name) => setScorer({ id, name })}
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
