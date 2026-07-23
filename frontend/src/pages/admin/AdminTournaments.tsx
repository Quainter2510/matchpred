import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  api,
  CreateTournamentBody,
  RoomScoring,
  TournamentRound,
  TournamentType,
} from "../../api/endpoints";

const DEFAULT_SCORING: RoomScoring = {
  points_exact: 5,
  points_diff: 2,
  points_outcome: 1,
  points_champion: 10,
  points_scorer: 10,
};

// Все типы доступны для создания.
const HIDDEN_TYPES: TournamentType[] = [];

export default function AdminTournaments() {
  const qc = useQueryClient();
  const navigate = useNavigate();

  const types = useQuery({
    queryKey: ["tournament-types"],
    queryFn: api.tournamentTypes,
  });

  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [type, setType] = useState<TournamentType>("rpl");
  const [season, setSeason] = useState<number>(new Date().getFullYear());
  const [firstRound, setFirstRound] = useState<string>("");
  const [lastRound, setLastRound] = useState<string>("");
  const [scoring, setScoring] = useState<RoomScoring>(DEFAULT_SCORING);

  const typeInfo = (types.data || []).find((t) => t.id === type);
  const needsSeason = !!typeInfo?.needs_season;
  const hasLeague = !!typeInfo?.has_league;

  // Туры лиги для выбора длительности «с тура по тур» (только лиговые типы,
  // кроме ЧМ). Загружаются по кнопке — это запрос к API-Football.
  const [roundsLoaded, setRoundsLoaded] = useState(false);
  const rounds = useMutation({
    mutationFn: () => api.availableRounds(type, season),
    onSuccess: (data) => {
      setRoundsLoaded(true);
      if (data.length) {
        setFirstRound((prev) => prev || data[0].round);
        setLastRound((prev) => prev || data[data.length - 1].round);
      }
    },
    onError: (e: any) =>
      alert(e.response?.data?.detail || "Не удалось загрузить туры лиги"),
  });
  const roundList: TournamentRound[] = rounds.data || [];

  // По выбранным турам вычисляем окно дат и дедлайн (первый матч окна).
  const window = useMemo(() => {
    const first = roundList.find((r) => r.round === firstRound);
    const last = roundList.find((r) => r.round === lastRound);
    return {
      starts_on: first?.first_tour_date ?? null,
      ends_on: last?.last_tour_date ?? null,
      first_match_at: first?.first_kickoff ?? null,
    };
  }, [roundList, firstRound, lastRound]);

  const create = useMutation({
    mutationFn: () => {
      const body: CreateTournamentBody = {
        name,
        password,
        tournament_type: type,
        scoring,
      };
      if (needsSeason) body.season = season;
      // Для лиговых турниров (не ЧМ) — окно по выбранным турам.
      if (hasLeague && type !== "world_cup") {
        body.starts_on = window.starts_on;
        body.ends_on = window.ends_on;
        body.first_match_at = window.first_match_at;
      }
      return api.createTournament(body);
    },
    onSuccess: (room) => {
      qc.invalidateQueries({ queryKey: ["my-rooms"] });
      navigate(`/room/${room.id}`);
    },
    onError: (e: any) =>
      alert(e.response?.data?.detail || "Не удалось создать турнир"),
  });

  const needRounds = hasLeague && type !== "world_cup";
  const canSubmit =
    name.trim().length >= 2 &&
    password.length >= 4 &&
    (!needRounds || (!!window.starts_on && !!window.ends_on));

  const num = (v: string) => Math.max(0, parseInt(v || "0", 10) || 0);

  return (
    <div className="card max-w-2xl space-y-4">
      <div>
        <h2 className="text-lg font-semibold">Добавить турнир</h2>
        <p className="text-sm text-slate-500">
          Тип задаёт лигу и вид спецпрогноза. Один тип можно создавать много раз
          — это будут независимые турниры со своими участниками и правилами.
        </p>
      </div>

      <label className="block">
        <span className="mb-1 block text-sm font-medium">Тип турнира</span>
        <select
          className="input w-full"
          value={type}
          onChange={(e) => {
            setType(e.target.value as TournamentType);
            setRoundsLoaded(false);
            setFirstRound("");
            setLastRound("");
          }}
        >
          {(types.data || [])
            .filter((t) => !HIDDEN_TYPES.includes(t.id))
            .map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}
              </option>
            ))}
        </select>
      </label>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="mb-1 block text-sm font-medium">Название</span>
          <input
            className="input w-full"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="напр. РПЛ — весна 2026"
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium">Пароль</span>
          <input
            className="input w-full"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="для вступления участников"
          />
        </label>
      </div>

      {needsSeason && (
        <label className="block max-w-[200px]">
          <span className="mb-1 block text-sm font-medium">Сезон</span>
          <input
            type="number"
            className="input w-full"
            value={season}
            onChange={(e) => {
              setSeason(num(e.target.value));
              setRoundsLoaded(false);
            }}
          />
          <span className="mt-1 block text-xs text-slate-500">
            Год начала сезона в API-Football (напр. 2025 для сезона 2025/26).
          </span>
        </label>
      )}

      {needRounds && (
        <div className="space-y-3 rounded-lg border border-slate-200 p-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Длительность (туры)</span>
            <button
              className="btn-ghost text-sm"
              onClick={() => rounds.mutate()}
              disabled={rounds.isPending}
            >
              {rounds.isPending ? "Загрузка…" : "Загрузить туры лиги"}
            </button>
          </div>
          {roundsLoaded && roundList.length === 0 && (
            <p className="text-sm text-amber-600">
              У этой лиги/сезона нет туров в API — проверьте сезон.
            </p>
          )}
          {roundList.length > 0 && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <label className="block">
                <span className="mb-1 block text-sm text-slate-600">С тура</span>
                <select
                  className="input w-full"
                  value={firstRound}
                  onChange={(e) => setFirstRound(e.target.value)}
                >
                  {roundList.map((r) => (
                    <option key={r.round} value={r.round}>
                      {r.round} ({r.first_tour_date})
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="mb-1 block text-sm text-slate-600">По тур</span>
                <select
                  className="input w-full"
                  value={lastRound}
                  onChange={(e) => setLastRound(e.target.value)}
                >
                  {roundList.map((r) => (
                    <option key={r.round} value={r.round}>
                      {r.round} ({r.last_tour_date})
                    </option>
                  ))}
                </select>
              </label>
            </div>
          )}
          {window.starts_on && window.ends_on && (
            <p className="text-xs text-slate-500">
              Окно: {window.starts_on} — {window.ends_on}. Дедлайн спецпрогноза —
              первый матч окна.
            </p>
          )}
        </div>
      )}

      <details className="rounded-lg border border-slate-200 p-3">
        <summary className="cursor-pointer text-sm font-medium">
          Правила начисления очков
        </summary>
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {(
            [
              ["points_exact", "Точный счёт"],
              ["points_diff", "Разница"],
              ["points_outcome", "Исход"],
              [
                "points_champion",
                typeInfo?.special_kind === "leader" ? "Лидер лиги" : "Победитель / чемпион",
              ],
              ["points_scorer", "Бомбардир"],
            ] as [keyof RoomScoring, string][]
          )
            .filter(([key]) => {
              // Бомбардир — только у ЧМ; спецочки за команду — не у custom.
              if (key === "points_scorer") return typeInfo?.special_kind === "wc";
              if (key === "points_champion")
                return typeInfo?.special_kind !== "none";
              return true;
            })
            .map(([key, label]) => (
              <label key={key} className="block">
                <span className="mb-1 block text-xs text-slate-600">{label}</span>
                <input
                  type="number"
                  className="input w-full"
                  value={scoring[key]}
                  onChange={(e) =>
                    setScoring({ ...scoring, [key]: num(e.target.value) })
                  }
                />
              </label>
            ))}
        </div>
      </details>

      <button
        className="btn-primary"
        onClick={() => create.mutate()}
        disabled={!canSubmit || create.isPending}
      >
        {create.isPending ? "Создание…" : "Создать турнир"}
      </button>
    </div>
  );
}
