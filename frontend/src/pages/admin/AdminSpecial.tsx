import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../../api/endpoints";
import PlayerSearch from "../../components/PlayerSearch";

export default function AdminSpecial() {
  const [scorer, setScorer] = useState<{ id: number | null; name: string | null }>({
    id: null,
    name: null,
  });

  const award = useMutation({
    mutationFn: () => api.scorerResult(scorer.id!, scorer.name!),
    onSuccess: (r: any) => alert(`Начислено игрокам: ${r.awarded}`),
  });

  return (
    <div className="card max-w-lg space-y-4">
      <h2 className="text-lg font-semibold">Лучший бомбардир турнира</h2>
      <p className="text-sm text-slate-500">
        Выберите итогового бомбардира и начислите 10 очков всем, кто его угадал.
        Победитель турнира начисляется автоматически при пересчёте после финала.
      </p>
      <PlayerSearch
        value={scorer}
        onSelect={(id, name) => setScorer({ id, name })}
      />
      <button
        className="btn-primary"
        disabled={!scorer.id || award.isPending}
        onClick={() => award.mutate()}
      >
        {award.isPending ? "Начисление…" : "Начислить очки за бомбардира"}
      </button>
    </div>
  );
}
