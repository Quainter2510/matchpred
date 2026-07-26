import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, SpecialKind } from "../api/endpoints";
import PlayerSearch from "../components/PlayerSearch";
import CountrySelect from "../components/CountrySelect";
import TeamName from "../components/TeamName";
import { useTeamName } from "../utils/useTeams";

const TEAM_KINDS: SpecialKind[] = ["leader", "stage_or_champion", "leader_scorer"];
const SCORER_KINDS: SpecialKind[] = ["wc", "leader_scorer"];

function teamLabel(kind: SpecialKind): string {
  if (kind === "wc") return "Чемпион турнира";
  if (kind === "stage_or_champion") return "Победитель / чемпион";
  return "Лидер лиги на финальный момент";
}

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

  const hasTeam = TEAM_KINDS.includes(specialKind);
  const hasScorer = SCORER_KINDS.includes(specialKind);
  // Команда-выбор для ЧМ — сборная (CountrySelect), для лиг — клуб (селект).
  const isClub = specialKind !== "wc";

  const teamName = useTeamName();
  const standings = useQuery({
    queryKey: ["standings", roomId],
    queryFn: () => api.standings(roomId),
    enabled: hasTeam && isClub,
  });
  const teams = useMemo(() => {
    const rows = standings.data?.groups.flatMap((g) => g.teams) || [];
    return Array.from(new Set(rows.map((t) => t.team))).sort((a, b) =>
      teamName(a).localeCompare(teamName(b), "ru")
    );
  }, [standings.data, teamName]);

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
        champion_team: hasTeam ? champion || null : null,
        top_scorer_name: hasScorer ? scorer.name : null,
        top_scorer_api_id: hasScorer ? scorer.id : null,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["special", roomId] }),
  });

  if (specialKind === "none") return null;
  if (isLoading) return null;
  const locked = data?.locked;
  const championSaved = !!data?.champion_team && champion === data.champion_team;
  const scorerSaved =
    !!data?.top_scorer_api_id && scorer.id === data.top_scorer_api_id;

  return (
    <section className="card space-y-3">
      <h2 className="text-lg font-semibold">Спецпрогнозы</h2>
      {locked && (
        <p className="rounded bg-amber-100 px-3 py-2 text-sm text-amber-800">
          Приём спецпрогнозов завершён.
          {hasTeam &&
            data?.champion_points != null &&
            ` ${teamLabel(specialKind)}: +${data.champion_points}.`}
          {hasScorer &&
            data?.scorer_points != null &&
            ` Бомбардир: +${data.scorer_points}.`}
        </p>
      )}

      {hasTeam && (
        <div>
          <label className="text-sm text-slate-600">{teamLabel(specialKind)}</label>
          {locked ? (
            <div className="input flex items-center bg-slate-50">
              {champion ? (
                <TeamName team={champion} />
              ) : (
                <span className="text-slate-400">—</span>
              )}
            </div>
          ) : !isClub ? (
            <CountrySelect
              value={champion}
              onChange={setChampion}
              highlight={championSaved}
            />
          ) : teams.length > 0 ? (
            <select
              className={`input ${championSaved ? "border-emerald-400 bg-emerald-50" : ""}`}
              value={champion}
              onChange={(e) => setChampion(e.target.value)}
            >
              <option value="">— выберите команду —</option>
              {teams.map((t) => (
                <option key={t} value={t}>
                  {teamName(t)}
                </option>
              ))}
            </select>
          ) : (
            <input
              className={`input ${championSaved ? "border-emerald-400 bg-emerald-50" : ""}`}
              value={champion}
              onChange={(e) => setChampion(e.target.value)}
              placeholder="Название команды"
            />
          )}
        </div>
      )}

      {hasScorer && (
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
