import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, SpecialKind } from "../api/endpoints";
import PlayerSearch from "../components/PlayerSearch";
import CountrySelect from "../components/CountrySelect";
import TeamName from "../components/TeamName";

export default function SpecialPredictionCard({
  roomId,
  specialKind = "wc",
}: {
  roomId: string;
  specialKind?: SpecialKind;
}) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["special", roomId],
    queryFn: () => api.mySpecial(roomId),
  });

  // Список команд турнира — для спецпрогноза «лидер лиги» (селект вместо ввода).
  const standings = useQuery({
    queryKey: ["standings", roomId],
    queryFn: () => api.standings(roomId),
    enabled: specialKind === "leader",
  });
  const teams = useMemo(() => {
    const rows = standings.data?.groups.flatMap((g) => g.teams) || [];
    return Array.from(new Set(rows.map((t) => t.team))).sort((a, b) =>
      a.localeCompare(b, "ru")
    );
  }, [standings.data]);

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
        // Лидер лиги — только команда; бомбардир не участвует.
        top_scorer_name: specialKind === "wc" ? scorer.name : null,
        top_scorer_api_id: specialKind === "wc" ? scorer.id : null,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["special", roomId] }),
  });

  // Типы без спецпрогноза (custom и пр.) — карточку не показываем.
  if (specialKind === "none" || specialKind === "stage_or_champion") return null;
  if (isLoading) return null;
  const locked = data?.locked;
  const isLeader = specialKind === "leader";

  const championSaved = !!data?.champion_team && champion === data.champion_team;
  const scorerSaved =
    !!data?.top_scorer_api_id && scorer.id === data.top_scorer_api_id;

  return (
    <section className="card space-y-3">
      <h2 className="text-lg font-semibold">
        {isLeader ? "Спецпрогноз" : "Спецпрогнозы"}
      </h2>
      {locked && (
        <p className="rounded bg-amber-100 px-3 py-2 text-sm text-amber-800">
          Приём спецпрогнозов завершён.
          {data?.champion_points != null &&
            ` ${isLeader ? "Лидер" : "Чемпион"}: +${data.champion_points}.`}
          {!isLeader &&
            data?.scorer_points != null &&
            ` Бомбардир: +${data.scorer_points}.`}
        </p>
      )}
      <div>
        <label className="text-sm text-slate-600">
          {isLeader ? "Лидер лиги на финальный момент" : "Чемпион турнира"}
        </label>
        {locked ? (
          <div className="input flex items-center bg-slate-50">
            {champion ? (
              <TeamName team={champion} />
            ) : (
              <span className="text-slate-400">—</span>
            )}
          </div>
        ) : isLeader ? (
          // Лидер лиги — команда клуба; выбор из команд турнира. Если таблица
          // ещё пуста, разрешаем ручной ввод названия.
          teams.length > 0 ? (
            <select
              className={`input ${
                championSaved ? "border-emerald-400 bg-emerald-50" : ""
              }`}
              value={champion}
              onChange={(e) => setChampion(e.target.value)}
            >
              <option value="">— выберите команду —</option>
              {teams.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          ) : (
            <input
              className={`input ${
                championSaved ? "border-emerald-400 bg-emerald-50" : ""
              }`}
              value={champion}
              onChange={(e) => setChampion(e.target.value)}
              placeholder="Название команды"
            />
          )
        ) : (
          <CountrySelect
            value={champion}
            onChange={setChampion}
            highlight={championSaved}
          />
        )}
      </div>
      {!isLeader && (
        <div>
          <label className="text-sm text-slate-600">Лучший бомбардир</label>
          <PlayerSearch
            value={scorer}
            disabled={locked}
            onSelect={(id, name) => setScorer({ id, name })}
            highlight={scorerSaved}
          />
        </div>
      )}
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
