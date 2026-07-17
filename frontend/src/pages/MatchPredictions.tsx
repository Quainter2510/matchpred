import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, Match, PlayerPrediction } from "../api/endpoints";
import { useAuth } from "../store/auth";
import { useViewAs } from "../store/viewAs";
import Avatar from "../components/Avatar";
import { LiveBadge } from "../components/MatchCard";
import MultiplierBadge from "../components/MultiplierBadge";
import TeamName from "../components/TeamName";
import Flag from "../components/Flag";
import { findCountry } from "../utils/countries";
import { classifyPrediction, HIT_BG } from "../utils/scoring";

// Очки начислены → сортируем по убыванию; сделавшие прогноз выше тех, кто
// без прогноза (у них прочерки); внутри — по нику.
function byPoints(a: PlayerPrediction, b: PlayerPrediction): number {
  const ap = a.points_awarded ?? -1;
  const bp = b.points_awarded ?? -1;
  if (bp !== ap) return bp - ap;
  const aHas = a.predicted_home != null;
  const bHas = b.predicted_home != null;
  if (aHas !== bHas) return aHas ? -1 : 1;
  if (!!b.is_exact !== !!a.is_exact) return b.is_exact ? 1 : -1;
  return a.nickname.localeCompare(b.nickname, "ru");
}

// Полоса распределения исходов: сколько прогнозов за победу 1-й команды,
// ничью и победу 2-й. Считается по сделанным (видимым) прогнозам.
function DistributionBar({
  preds,
  match,
}: {
  preds: PlayerPrediction[];
  match: Match;
}) {
  const made = preds.filter(
    (p) => p.predicted_home != null && p.predicted_away != null
  );
  const total = made.length;
  if (!total) return null;

  let home = 0;
  let draw = 0;
  let away = 0;
  for (const p of made) {
    const diff = p.predicted_home! - p.predicted_away!;
    if (diff > 0) home++;
    else if (diff < 0) away++;
    else draw++;
  }
  const pct = (n: number) => `${Math.round((n / total) * 100)}%`;
  const homeC = findCountry(match.home_team);
  const awayC = findCountry(match.away_team);
  const segs = [
    {
      n: home,
      color: "bg-sky-500",
      label: match.home_team,
      icon: homeC ? <Flag code={homeC.code} title={match.home_team} /> : null,
    },
    {
      n: draw,
      color: "bg-slate-400",
      label: "Ничья",
      icon: <span className="leading-none">✕</span>,
    },
    {
      n: away,
      color: "bg-indigo-500",
      label: match.away_team,
      icon: awayC ? <Flag code={awayC.code} title={match.away_team} /> : null,
    },
  ];

  return (
    <div className="mb-4 flex h-7 w-full overflow-hidden rounded-lg bg-slate-100 text-sm font-bold tabular-nums text-white">
      {segs.map((s, i) =>
        s.n > 0 ? (
          <div
            key={i}
            className={`flex min-w-[2.75rem] items-center justify-center gap-1 overflow-hidden ${s.color}`}
            style={{ width: pct(s.n) }}
            title={`${s.label}: ${s.n} (${pct(s.n)})`}
          >
            {s.icon}
            {s.n}
          </div>
        ) : null
      )}
    </div>
  );
}

function isFinished(m: Match | undefined): boolean {
  return (
    !!m &&
    m.status === "finished" &&
    m.home_score_ft != null &&
    m.away_score_ft != null
  );
}

// Единая цветовая схема: точный — зелёный, разница — синий, исход — янтарный,
// промах — красный. Категория считается по счёту, а не по очкам, поэтому
// не зависит от правил комнаты и коэффициента матча. Пропущенный прогноз на
// завершённом матче — как промах (0 очков, красная строка).
function rowTint(p: PlayerPrediction, m: Match | undefined): string {
  if (!isFinished(m)) return "";
  if (p.predicted_home == null || p.predicted_away == null)
    return HIT_BG.miss;
  if (p.points_awarded == null) return "";
  return HIT_BG[
    classifyPrediction(
      p.predicted_home,
      p.predicted_away,
      m!.home_score_ft!,
      m!.away_score_ft!
    )
  ];
}

export default function MatchPredictions() {
  const { roomId, id } = useParams<{ roomId: string; id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const adminMode = useViewAs((s) => s.adminMode);
  const isSuper = useAuth((s) => s.isSuperadmin()) && adminMode;

  // Суперадмин может проставить/поправить прогноз участника после дедлайна —
  // в том числе на завершённом матче (очки снимутся и начислятся заново).
  const [editing, setEditing] = useState<string | null>(null);
  const [editH, setEditH] = useState("");
  const [editA, setEditA] = useState("");
  const saveEdit = useMutation({
    mutationFn: (userId: string) =>
      api.adminSetPrediction(roomId!, id!, userId, Number(editH), Number(editA)),
    onSuccess: () => {
      setEditing(null);
      qc.invalidateQueries({ queryKey: ["match-preds", roomId, id] });
      // На завершённом матче правка меняет очки — обновляем и таблицу лидеров.
      qc.invalidateQueries({ queryKey: ["leaderboard"] });
      qc.invalidateQueries({ queryKey: ["days", roomId] });
    },
    onError: (e: any) =>
      alert(e.response?.data?.detail || "Не удалось сохранить прогноз"),
  });
  // Раз в минуту подтягиваем live-счёт и очки, начисленные после завершения.
  const match = useQuery({
    queryKey: ["match", roomId, id],
    queryFn: () => api.match(roomId!, id!),
    enabled: !!roomId && !!id,
    refetchInterval: 60_000,
  });
  const preds = useQuery({
    queryKey: ["match-preds", roomId, id],
    queryFn: () => api.matchPredictions(roomId!, id!),
    enabled: !!roomId && !!id,
    refetchInterval: 60_000,
  });

  return (
    <div className="space-y-4">
      <button onClick={() => navigate(-1)} className="btn-ghost">
        ← Назад
      </button>
      {match.data && (
        <h1 className="flex flex-wrap items-center gap-2 text-xl font-bold">
          <TeamName team={match.data.home_team} />
          <span className={match.data.status === "live" ? "text-red-600" : ""}>
            {match.data.home_score_ft ?? ""}
            {match.data.home_score_ft != null && match.data.away_score_ft != null
              ? " : "
              : " — "}
            {match.data.away_score_ft ?? ""}
          </span>
          <TeamName team={match.data.away_team} />
          {match.data.status === "live" && <LiveBadge />}
          <MultiplierBadge value={match.data.points_multiplier} large />
        </h1>
      )}
      <div className="card">
        {preds.isError ? (
          <p className="text-slate-500">Прогнозы скрыты до начала матча.</p>
        ) : preds.isLoading ? (
          <p className="text-slate-500">Загрузка…</p>
        ) : (
          <>
          {match.data && (
            <DistributionBar preds={preds.data || []} match={match.data} />
          )}
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-slate-500">
                <th className="py-2">Игрок</th>
                <th className="text-center">Прогноз</th>
                <th className="text-right">Очки</th>
              </tr>
            </thead>
            <tbody>
              {[...(preds.data || [])].sort(byPoints).map((p) => (
                <tr key={p.user_id} className={`border-b ${rowTint(p, match.data)}`}>
                  <td className="flex items-center gap-2 py-2">
                    <Avatar url={p.avatar_url} nick={p.nickname} className="h-6 w-6" textClassName="text-xs" />
                    <Link
                      to={`/room/${roomId}/player/${p.user_id}`}
                      className="hover:text-brand hover:underline"
                    >
                      {p.nickname}
                    </Link>
                  </td>
                  <td className="text-center font-medium">
                    {editing === p.user_id ? (
                      <span className="inline-flex items-center gap-1">
                        <input
                          className="w-10 rounded border px-1 text-center"
                          value={editH}
                          onChange={(e) => setEditH(e.target.value)}
                        />
                        :
                        <input
                          className="w-10 rounded border px-1 text-center"
                          value={editA}
                          onChange={(e) => setEditA(e.target.value)}
                        />
                        <button
                          className="px-1 font-bold text-emerald-600 hover:text-emerald-700"
                          title="Сохранить"
                          disabled={editH === "" || editA === "" || saveEdit.isPending}
                          onClick={() => saveEdit.mutate(p.user_id)}
                        >
                          ✓
                        </button>
                        <button
                          className="px-1 text-slate-400 hover:text-slate-600"
                          title="Отмена"
                          onClick={() => setEditing(null)}
                        >
                          ✕
                        </button>
                      </span>
                    ) : (
                      <>
                        {p.predicted_home != null && p.predicted_away != null ? (
                          `${p.predicted_home}:${p.predicted_away}`
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                        {isSuper && (
                          <button
                            className="ml-1.5 text-slate-400 hover:text-brand"
                            title="Изменить прогноз участника (суперадмин)"
                            onClick={() => {
                              setEditing(p.user_id);
                              setEditH(p.predicted_home?.toString() ?? "");
                              setEditA(p.predicted_away?.toString() ?? "");
                            }}
                          >
                            ✎
                          </button>
                        )}
                      </>
                    )}
                  </td>
                  <td className="text-right">
                    {p.points_awarded != null ? (
                      <span className={p.is_exact ? "font-bold text-emerald-600" : ""}>
                        +{p.points_awarded}
                      </span>
                    ) : p.predicted_home == null && isFinished(match.data) ? (
                      // Пропущенный прогноз на завершённом матче = 0 очков.
                      <span className="font-semibold text-rose-600">0</span>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </>
        )}
      </div>
    </div>
  );
}
