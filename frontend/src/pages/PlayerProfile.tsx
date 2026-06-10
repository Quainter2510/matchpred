import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { api, PlayerProfile as Profile, PlayerProfileMatch, RoomScoring } from "../api/endpoints";
import TeamName from "../components/TeamName";
import { formatDate, formatTime } from "../utils/dates";
import { formatStage } from "../utils/stage";

function Avatar({ url, nick, size }: { url: string | null; nick: string; size: string }) {
  return url ? (
    <img src={url} className={`${size} rounded-full object-cover`} />
  ) : (
    <div className={`${size} flex items-center justify-center rounded-full bg-slate-300 font-semibold text-slate-600`}>
      {nick[0]?.toUpperCase()}
    </div>
  );
}

// Colour of a match row by points earned (uses the room's own point values).
function rowClass(m: PlayerProfileMatch, s: RoomScoring | null | undefined): string {
  if (m.points_awarded == null) return "border-slate-200 bg-white";
  if (m.is_exact || (s && m.points_awarded >= s.points_exact))
    return "border-emerald-300 bg-emerald-50";
  if (s && m.points_awarded === s.points_diff) return "border-sky-300 bg-sky-50";
  if (m.points_awarded > 0) return "border-amber-300 bg-amber-50";
  return "border-rose-200 bg-rose-50";
}

function score(h: number | null, a: number | null): string {
  return h == null || a == null ? "—:—" : `${h}:${a}`;
}

export default function PlayerProfile() {
  const { roomId, userId } = useParams<{ roomId: string; userId: string }>();
  const navigate = useNavigate();
  const [compact, setCompact] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["player", roomId, userId],
    queryFn: () => api.playerProfile(roomId!, userId!),
    enabled: !!roomId && !!userId,
  });
  const room = useQuery({
    queryKey: ["room", roomId],
    queryFn: () => api.roomDetail(roomId!),
    enabled: !!roomId,
  });
  const scoring = room.data?.scoring;

  const firstUpcoming = data?.matches.find((m) => !m.started);

  // Shrink the header once the user scrolls past the big profile block.
  useEffect(() => {
    const onScroll = () => setCompact(window.scrollY > 140);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Land directly on the first not-yet-started match.
  useEffect(() => {
    if (!firstUpcoming) return;
    const t = setTimeout(() => {
      document
        .getElementById(`m-${firstUpcoming.match_id}`)
        ?.scrollIntoView({ block: "start" });
    }, 60);
    return () => clearTimeout(t);
  }, [firstUpcoming?.match_id]);

  const jumpToUpcoming = () => {
    if (firstUpcoming)
      document
        .getElementById(`m-${firstUpcoming.match_id}`)
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  if (isLoading || !data) return <p className="text-slate-500">Загрузка…</p>;

  const placeStr = data.place ? `#${data.place}` : "—";

  return (
    <div className="relative">
      {/* Sticky header: full at the top, compact once scrolled. */}
      <div className="sticky top-0 z-20 -mx-4 border-b border-slate-200 bg-white/95 px-4 backdrop-blur">
        <div className="flex items-center gap-2 py-2">
          <button onClick={() => navigate(-1)} className="text-sm text-slate-500 hover:underline">
            ← Назад
          </button>
        </div>
        {compact ? (
          <div className="flex items-center gap-3 pb-2">
            <Avatar url={data.avatar_url} nick={data.nickname} size="h-9 w-9" />
            <div className="min-w-0 flex-1 truncate font-semibold">{data.nickname}</div>
            <div className="flex gap-3 text-sm">
              <span className="text-slate-500">{placeStr}</span>
              <span className="font-semibold">{data.total_points} очк.</span>
              <span className="text-emerald-600">{data.exact_scores_count}✓</span>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-4 pb-4 pt-2">
            <Avatar url={data.avatar_url} nick={data.nickname} size="h-20 w-20" />
            <div>
              <div className="text-2xl font-bold">{data.nickname}</div>
              <div className="mt-2 flex gap-4 text-sm">
                <div>
                  <div className="text-slate-400">Место</div>
                  <div className="text-lg font-semibold">{placeStr}</div>
                </div>
                <div>
                  <div className="text-slate-400">Очки</div>
                  <div className="text-lg font-semibold">{data.total_points}</div>
                </div>
                <div>
                  <div className="text-slate-400">Точные счёта</div>
                  <div className="text-lg font-semibold text-emerald-600">
                    {data.exact_scores_count}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Matches */}
      <div className="mt-4 space-y-2">
        {data.matches.map((m) => (
          <div
            key={m.match_id}
            id={`m-${m.match_id}`}
            className={`scroll-mt-28 rounded-lg border p-3 ${rowClass(m, scoring)}`}
          >
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>
                {formatDate(m.match_date)} {formatTime(m.kickoff_at)} ·{" "}
                {formatStage(m.stage, m.group_name)}
              </span>
              <span>
                {m.points_awarded != null ? (
                  <span className={m.is_exact ? "font-bold text-emerald-700" : "font-medium"}>
                    +{m.points_awarded}
                  </span>
                ) : (
                  "—"
                )}
              </span>
            </div>
            <div className="mt-1 grid grid-cols-3 items-center gap-2">
              <TeamName team={m.home_team} flagSide="right" className="justify-end text-right font-medium" />
              <div className="text-center">
                <div className="text-lg font-bold">
                  {m.status === "finished" ? score(m.home_score_ft, m.away_score_ft) : "—:—"}
                </div>
                <div className="text-xs text-slate-500">
                  прогноз: {score(m.predicted_home, m.predicted_away)}
                </div>
              </div>
              <TeamName team={m.away_team} className="justify-start text-left font-medium" />
            </div>
          </div>
        ))}
      </div>

      {/* Jump to the first upcoming match */}
      {firstUpcoming && (
        <button
          onClick={jumpToUpcoming}
          title="К ближайшему матчу"
          className="fixed bottom-24 right-4 z-30 flex h-11 w-11 items-center justify-center rounded-full bg-brand text-white shadow-lg hover:bg-brand-dark md:bottom-6"
        >
          ↓
        </button>
      )}
    </div>
  );
}
