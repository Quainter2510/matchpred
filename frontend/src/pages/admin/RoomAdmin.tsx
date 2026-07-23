import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, RoomDetail, RoomScoring } from "../../api/endpoints";
import { useAuth } from "../../store/auth";
import { formatDate, formatTime } from "../../utils/dates";
import TeamName from "../../components/TeamName";
import MultiplierBadge from "../../components/MultiplierBadge";
import PlayerSearch from "../../components/PlayerSearch";

const MULTIPLIERS = [0, 1, 2, 3];

function ruleFields(specialKind: string): { key: keyof RoomScoring; label: string }[] {
  const base: { key: keyof RoomScoring; label: string }[] = [
    { key: "points_exact", label: "Точный счёт" },
    { key: "points_diff", label: "Разница мячей" },
    { key: "points_outcome", label: "Исход (победитель/ничья)" },
  ];
  if (specialKind === "leader") {
    base.push({ key: "points_champion", label: "Лидер лиги" });
  } else if (specialKind === "wc") {
    base.push({ key: "points_champion", label: "Чемпион турнира" });
    base.push({ key: "points_scorer", label: "Лучший бомбардир" });
  }
  return base;
}

function ScoringRules({ room }: { room: RoomDetail }) {
  const RULE_FIELDS = ruleFields(room.special_kind);
  const qc = useQueryClient();
  const [vals, setVals] = useState<RoomScoring>(
    room.scoring || {
      points_exact: 5,
      points_diff: 2,
      points_outcome: 1,
      points_champion: 10,
      points_scorer: 10,
    }
  );
  useEffect(() => {
    if (room.scoring) setVals(room.scoring);
  }, [room.scoring]);

  const save = useMutation({
    mutationFn: () => api.updateRoomRules(room.id, vals),
    onSuccess: () => {
      alert("Правила начисления обновлены");
      qc.invalidateQueries({ queryKey: ["room", room.id] });
    },
    onError: (e: any) => alert(e.response?.data?.detail || "Ошибка"),
  });

  return (
    <section className="card max-w-lg space-y-3">
      <h2 className="text-lg font-semibold">Правила начисления очков</h2>
      <p className="text-sm text-slate-500">
        Действуют для этого соревнования. Применяются к ещё не начисленным прогнозам —
        задавайте до завершения матчей.
      </p>
      {RULE_FIELDS.map((f) => (
        <label key={f.key} className="flex items-center justify-between gap-3">
          <span className="text-sm">{f.label}</span>
          <input
            type="number"
            min={0}
            max={1000}
            className="w-24 rounded-lg border border-slate-300 px-2 py-1 text-center"
            value={vals[f.key]}
            onChange={(e) =>
              setVals({ ...vals, [f.key]: Math.max(0, parseInt(e.target.value || "0", 10)) })
            }
          />
        </label>
      ))}
      <button className="btn-primary" onClick={() => save.mutate()} disabled={save.isPending}>
        {save.isPending ? "Сохранение…" : "Сохранить правила"}
      </button>
    </section>
  );
}

function RulesText({ room }: { room: RoomDetail }) {
  const qc = useQueryClient();
  const [text, setText] = useState(room.rules_text ?? "");
  useEffect(() => setText(room.rules_text ?? ""), [room.rules_text]);

  const save = useMutation({
    mutationFn: () => api.updateRoomRulesText(room.id, text),
    onSuccess: () => {
      alert("Регламент сохранён");
      qc.invalidateQueries({ queryKey: ["room", room.id] });
    },
    onError: (e: any) => alert(e.response?.data?.detail || "Ошибка"),
  });

  return (
    <section className="card max-w-lg space-y-3">
      <h2 className="text-lg font-semibold">Регламент соревнования</h2>
      <p className="text-sm text-slate-500">
        Участники видят этот текст по кнопке «i» рядом с названием соревнования.
        Если оставить пустым — показывается стандартное описание начисления очков.
      </p>
      <textarea
        className="input min-h-[10rem]"
        rows={8}
        maxLength={10000}
        placeholder="Например: правила, сроки, призы…"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <button
        className="btn-primary"
        onClick={() => save.mutate()}
        disabled={save.isPending}
      >
        {save.isPending ? "Сохранение…" : "Сохранить регламент"}
      </button>
    </section>
  );
}

function ArchiveControl({ room }: { room: RoomDetail }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const archive = useMutation({
    mutationFn: () => api.archiveRoom(room.id, room.is_active),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["room", room.id] });
      qc.invalidateQueries({ queryKey: ["my-rooms"] });
      if (room.is_active) navigate("/");
    },
  });
  return (
    <section className="card max-w-lg space-y-3">
      <h2 className="text-lg font-semibold">
        {room.is_active ? "Архивировать соревнование" : "Восстановить соревнование"}
      </h2>
      <p className="text-sm text-slate-500">
        {room.is_active
          ? "Соревнование станет доступно только для просмотра: новые прогнозы и начисление очков прекратятся, таблица сохранится."
          : "Соревнование снова станет активным: приём прогнозов и начисление возобновятся."}
      </p>
      <button
        className={room.is_active ? "btn-ghost" : "btn-primary"}
        onClick={() => archive.mutate()}
        disabled={archive.isPending}
      >
        {room.is_active ? "В архив" : "Восстановить"}
      </button>
    </section>
  );
}

function Members({ roomId }: { roomId: string }) {
  const qc = useQueryClient();
  const isSuper = useAuth((s) => s.isSuperadmin());
  const members = useQuery({
    queryKey: ["room-members", roomId],
    queryFn: () => api.roomMembers(roomId),
  });
  const invalidate = () => qc.invalidateQueries({ queryKey: ["room-members", roomId] });

  const role = useMutation({
    mutationFn: ({ uid, r }: { uid: string; r: string }) => api.changeRole(roomId, uid, r),
    onSuccess: invalidate,
  });
  const participation = useMutation({
    mutationFn: ({ uid, c }: { uid: string; c: boolean }) =>
      api.setParticipation(roomId, uid, c),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: (uid: string) => api.removeMember(roomId, uid),
    onSuccess: invalidate,
  });
  const transfer = useMutation({
    mutationFn: (uid: string) => api.transferSuperadmin(uid),
    onSuccess: () => {
      alert("Роль суперадмина передана");
      invalidate();
    },
  });

  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-slate-500">
            <th className="py-2">Игрок</th>
            <th>Роль</th>
            <th>Очки</th>
            <th>Участие</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {(members.data || []).map((m) => (
            <tr key={m.user_id} className="border-b">
              <td className="py-2">{m.nickname}</td>
              <td>
                {m.system_role === "superadmin" ? (
                  <span className="font-semibold text-brand">Суперадмин</span>
                ) : (
                  <select
                    className="rounded border px-2 py-1"
                    value={m.room_role}
                    onChange={(e) => role.mutate({ uid: m.user_id, r: e.target.value })}
                  >
                    <option value="player">Игрок</option>
                    <option value="admin">Админ</option>
                  </select>
                )}
              </td>
              <td>{m.total_points}</td>
              <td>
                <input
                  type="checkbox"
                  checked={m.participation_confirmed}
                  onChange={(e) =>
                    participation.mutate({ uid: m.user_id, c: e.target.checked })
                  }
                />
              </td>
              <td className="space-x-2 text-right">
                {isSuper && m.system_role !== "superadmin" && (
                  <button
                    className="text-xs text-brand hover:underline"
                    onClick={() => {
                      if (confirm(`Передать роль суперадмина игроку ${m.nickname}?`))
                        transfer.mutate(m.user_id);
                    }}
                  >
                    Суперадмин
                  </button>
                )}
                {m.system_role !== "superadmin" && (
                  <button
                    className="text-xs text-red-600 hover:underline"
                    onClick={() => {
                      if (confirm(`Удалить ${m.nickname} из соревнования?`))
                        remove.mutate(m.user_id);
                    }}
                  >
                    Удалить
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RoomPassword({ roomId }: { roomId: string }) {
  const [pwd, setPwd] = useState("");
  const change = useMutation({
    mutationFn: () => api.changeRoomPassword(roomId, pwd),
    onSuccess: () => {
      alert("Пароль соревнования обновлён");
      setPwd("");
    },
    onError: (e: any) => alert(e.response?.data?.detail || "Ошибка"),
  });
  return (
    <section className="card max-w-lg space-y-3">
      <h2 className="text-lg font-semibold">Пароль соревнования</h2>
      <input
        type="text"
        className="input"
        placeholder="Новый пароль"
        value={pwd}
        onChange={(e) => setPwd(e.target.value)}
      />
      <button
        className="btn-primary"
        disabled={pwd.length < 4 || change.isPending}
        onClick={() => change.mutate()}
      >
        Сменить пароль
      </button>
    </section>
  );
}

function Multipliers({ roomId }: { roomId: string }) {
  const qc = useQueryClient();
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [tourMult, setTourMult] = useState(1);
  const matches = useQuery({
    queryKey: ["room-admin-matches", roomId, date],
    queryFn: () => api.matchesByDate(roomId, date),
  });
  const invalidate = () => qc.invalidateQueries();
  const setMult = useMutation({
    mutationFn: ({ id, m }: { id: string; m: number }) =>
      api.setMatchMultiplier(roomId, id, m),
    onSuccess: invalidate,
    onError: (e: any) => alert(e.response?.data?.detail || "Ошибка"),
  });
  const tour = useMutation({
    mutationFn: () => api.setTourMultiplier(roomId, date, tourMult),
    onSuccess: invalidate,
    onError: (e: any) => alert(e.response?.data?.detail || "Ошибка"),
  });

  return (
    <section className="card space-y-3">
      <h2 className="text-lg font-semibold">Коэффициенты матчей</h2>
      <p className="text-sm text-slate-500">
        Действуют только в этом соревновании. ×0 аннулирует матч (очки 0, точный
        счёт не идёт в тайбрейк). У завершённого матча смена коэффициента
        пересчитывает очки.
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="date"
          className="input w-auto"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
        <span className="ml-auto flex items-center gap-2 text-sm">
          На весь тур:
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
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-slate-500">
              <th className="py-2">Когда</th>
              <th>Матч</th>
              <th>Кэф.</th>
            </tr>
          </thead>
          <tbody>
            {(matches.data || []).map((m) => (
              <tr key={m.id} className="border-b">
                <td className="py-2 text-xs text-slate-500">
                  {formatTime(m.kickoff_at)}
                </td>
                <td>
                  <span className="inline-flex flex-wrap items-center gap-1.5">
                    <TeamName team={m.home_team} />
                    <span className="text-slate-400">—</span>
                    <TeamName team={m.away_team} />
                    <MultiplierBadge value={m.points_multiplier} />
                  </span>
                </td>
                <td>
                  <select
                    className="rounded border px-1 py-1 text-sm"
                    value={m.points_multiplier}
                    disabled={setMult.isPending}
                    onChange={(e) =>
                      setMult.mutate({ id: m.id, m: Number(e.target.value) })
                    }
                  >
                    {MULTIPLIERS.map((x) => (
                      <option key={x} value={x}>
                        ×{x}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!matches.data?.length && (
          <p className="text-slate-500">Нет матчей на эту дату.</p>
        )}
      </div>
    </section>
  );
}

function ScorerResult({ roomId }: { roomId: string }) {
  const qc = useQueryClient();
  const [scorer, setScorer] = useState<{ id: number | null; name: string | null }>({
    id: null,
    name: null,
  });
  const award = useMutation({
    mutationFn: () => api.scorerResult(roomId, scorer.id!, scorer.name!),
    onSuccess: (r: any) => {
      alert(`Начислено игрокам: ${r.awarded}`);
      qc.invalidateQueries();
    },
    onError: (e: any) => alert(e.response?.data?.detail || "Ошибка"),
  });

  return (
    <section className="card max-w-lg space-y-3">
      <h2 className="text-lg font-semibold">Лучший бомбардир турнира</h2>
      <p className="text-sm text-slate-500">
        Выберите итогового бомбардира и начислите очки всем, кто его угадал —
        только в этом соревновании. Победитель турнира начисляется автоматически
        при пересчёте после финала.
      </p>
      <PlayerSearch value={scorer} onSelect={(id, name) => setScorer({ id, name })} />
      <button
        className="btn-primary"
        disabled={!scorer.id || award.isPending}
        onClick={() => award.mutate()}
      >
        {award.isPending ? "Начисление…" : "Начислить очки за бомбардира"}
      </button>
    </section>
  );
}

// Итоговый лидер лиги (спецпрогноз типа `leader`, напр. РПЛ) — начисляет очки
// вручную, аналогично бомбардиру, но по команде-победителю.
function LeaderResult({ roomId }: { roomId: string }) {
  const qc = useQueryClient();
  const standings = useQuery({
    queryKey: ["standings", roomId],
    queryFn: () => api.standings(roomId),
  });
  const teams = Array.from(
    new Set((standings.data?.groups.flatMap((g) => g.teams) || []).map((t) => t.team))
  ).sort((a, b) => a.localeCompare(b, "ru"));
  const [team, setTeam] = useState("");

  const award = useMutation({
    mutationFn: () => api.leaderResult(roomId, team),
    onSuccess: (r: any) => {
      alert(`Начислено игрокам: ${r.awarded}`);
      qc.invalidateQueries();
    },
    onError: (e: any) => alert(e.response?.data?.detail || "Ошибка"),
  });

  return (
    <section className="card max-w-lg space-y-3">
      <h2 className="text-lg font-semibold">Итоговый лидер лиги</h2>
      <p className="text-sm text-slate-500">
        Укажите команду-лидера на финальный момент и начислите очки всем, кто её
        угадал — только в этом соревновании.
      </p>
      {teams.length > 0 ? (
        <select className="input" value={team} onChange={(e) => setTeam(e.target.value)}>
          <option value="">— выберите команду —</option>
          {teams.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      ) : (
        <input
          className="input"
          value={team}
          onChange={(e) => setTeam(e.target.value)}
          placeholder="Название команды"
        />
      )}
      <button
        className="btn-primary"
        disabled={!team.trim() || award.isPending}
        onClick={() => award.mutate()}
      >
        {award.isPending ? "Начисление…" : "Начислить очки за лидера"}
      </button>
    </section>
  );
}

export default function RoomAdmin() {
  const { roomId } = useParams<{ roomId: string }>();
  const isSuper = useAuth((s) => s.isSuperadmin());
  const room = useQuery({
    queryKey: ["room", roomId],
    queryFn: () => api.roomDetail(roomId!),
    enabled: !!roomId,
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link to={`/room/${roomId}`} className="btn-ghost">
          ← Назад
        </Link>
        <h1 className="text-2xl font-bold">
          Управление: {room.data?.name}
          {room.data && !room.data.is_active && (
            <span className="ml-2 text-sm text-slate-400">(архив)</span>
          )}
        </h1>
      </div>
      <Members roomId={roomId!} />
      <Multipliers roomId={roomId!} />
      {/* Итоговый результат спецпрогноза — по типу турнира. */}
      {room.data?.special_kind === "wc" && <ScorerResult roomId={roomId!} />}
      {room.data?.special_kind === "leader" && <LeaderResult roomId={roomId!} />}
      <RoomPassword roomId={roomId!} />
      {room.data && <RulesText room={room.data} />}
      {isSuper && room.data && <ScoringRules room={room.data} />}
      {isSuper && room.data && <ArchiveControl room={room.data} />}
    </div>
  );
}
