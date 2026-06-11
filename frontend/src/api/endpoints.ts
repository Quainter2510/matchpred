import { client, API_BASE } from "./client";

export interface Me {
  id: string;
  nickname: string;
  avatar_url: string | null;
  system_role: "superadmin" | "user";
  has_rooms: boolean;
  is_any_admin: boolean;
  vk_linked: boolean;
}

export interface Room {
  id: string;
  name: string;
  member_count: number;
  is_member: boolean;
  is_active: boolean;
  my_role: "admin" | "player" | null;
}

export interface RoomScoring {
  points_exact: number;
  points_diff: number;
  points_outcome: number;
  points_champion: number;
  points_scorer: number;
}

export interface RoomDetail extends Room {
  first_match_at: string;
  total_points: number | null;
  place: number | null;
  scoring: RoomScoring | null;
  rules_text: string | null;
}

export interface MatchDay {
  date: string;
  match_count: number;
  my_predictions_count: number;
  first_kickoff_at: string;
  multiplier: number | null;
}

export interface MyPrediction {
  predicted_home: number;
  predicted_away: number;
  points_awarded: number | null;
  is_exact: boolean | null;
}

export interface Match {
  id: string;
  api_football_id: number | null;
  match_date: string;
  kickoff_at: string;
  stage: string;
  group_name: string | null;
  home_team: string;
  away_team: string;
  home_score_ft: number | null;
  away_score_ft: number | null;
  status: string;
  points_multiplier: number;
  my_prediction: MyPrediction | null;
}

export interface PlayerPrediction {
  user_id: string;
  nickname: string;
  avatar_url: string | null;
  predicted_home: number;
  predicted_away: number;
  points_awarded: number | null;
  is_exact: boolean | null;
}

export interface LeaderboardEntry {
  place: number;
  user_id: string;
  nickname: string;
  avatar_url: string | null;
  total_points: number;
  exact_scores_count: number;
  has_champion: boolean;
  has_scorer: boolean;
  champion_correct: boolean;
  scorer_correct: boolean;
  participation_confirmed: boolean;
  champion_team: string | null;
  top_scorer_name: string | null;
}

export interface SpecialPrediction {
  champion_team: string | null;
  top_scorer_name: string | null;
  top_scorer_api_id: number | null;
  champion_points: number | null;
  scorer_points: number | null;
  locked: boolean;
}

export interface RoomMember {
  user_id: string;
  nickname: string;
  avatar_url: string | null;
  system_role: string;
  room_role: string;
  total_points: number;
  exact_scores_count: number;
  participation_confirmed: boolean;
}

export interface PlayerProfileMatch {
  match_id: string;
  match_date: string;
  kickoff_at: string;
  stage: string;
  group_name: string | null;
  home_team: string;
  away_team: string;
  status: string;
  home_score_ft: number | null;
  away_score_ft: number | null;
  started: boolean;
  predicted_home: number | null;
  predicted_away: number | null;
  points_awarded: number | null;
  is_exact: boolean | null;
}

export interface PlayerProfile {
  user_id: string;
  nickname: string;
  avatar_url: string | null;
  place: number | null;
  total_points: number;
  exact_scores_count: number;
  diff_count: number;
  outcome_count: number;
  is_self: boolean;
  specials_revealed: boolean;
  first_match_at: string;
  champion_team: string | null;
  top_scorer_name: string | null;
  matches: PlayerProfileMatch[];
}

export interface AuditEntry {
  id: number;
  created_at: string;
  actor_id: string | null;
  actor_nickname: string | null;
  event_type: string;
  target_id: string | null;
  details: Record<string, unknown> | null;
}

const r = (roomId: string) => `/rooms/${roomId}`;

export const api = {
  // ---- auth ----
  me: () => client.get<Me>("/auth/me").then((x) => x.data),
  updateNickname: (nickname: string) =>
    client.patch<Me>("/auth/me", { nickname }).then((x) => x.data),
  uploadAvatar: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return client.post<Me>("/auth/me/avatar", fd).then((x) => x.data);
  },
  telegramVerify: (data: Record<string, unknown>) =>
    client
      .post<{ access_token: string; is_new_user: boolean }>(
        "/auth/telegram/verify",
        data
      )
      .then((x) => x.data),
  logout: () => client.post("/auth/logout"),
  yandexLoginUrl: () => `${API_BASE}/auth/yandex/login`,
  vkLinkCode: () =>
    client
      .post<{ code: string; bot_url: string | null }>("/auth/vk/link-code")
      .then((x) => x.data),

  // ---- rooms ----
  listRooms: (q?: string) =>
    client.get<Room[]>("/rooms", { params: q ? { q } : {} }).then((x) => x.data),
  myRooms: () => client.get<Room[]>("/rooms/my").then((x) => x.data),
  createRoom: (name: string, password: string, first_match_at?: string) =>
    client
      .post<RoomDetail>("/rooms", { name, password, first_match_at })
      .then((x) => x.data),
  joinRoom: (roomId: string, password: string) =>
    client.post<Room>(`${r(roomId)}/join`, { password }).then((x) => x.data),
  roomDetail: (roomId: string) =>
    client.get<RoomDetail>(r(roomId)).then((x) => x.data),
  deleteRoom: (roomId: string) => client.delete(r(roomId)).then((x) => x.data),
  archiveRoom: (roomId: string, archived: boolean) =>
    client.patch(`${r(roomId)}/archive`, { archived }).then((x) => x.data),
  updateRoomRules: (roomId: string, scoring: RoomScoring) =>
    client.patch<RoomScoring>(`${r(roomId)}/rules`, scoring).then((x) => x.data),
  updateRoomRulesText: (roomId: string, rules_text: string) =>
    client.patch(`${r(roomId)}/rules-text`, { rules_text }).then((x) => x.data),

  // room members (room admin)
  roomMembers: (roomId: string) =>
    client.get<RoomMember[]>(`${r(roomId)}/members`).then((x) => x.data),
  changeRole: (roomId: string, uid: string, role: string) =>
    client.patch(`${r(roomId)}/members/${uid}/role`, { role }).then((x) => x.data),
  setParticipation: (roomId: string, uid: string, confirmed: boolean) =>
    client
      .patch(`${r(roomId)}/members/${uid}/participation`, { confirmed })
      .then((x) => x.data),
  removeMember: (roomId: string, uid: string) =>
    client.delete(`${r(roomId)}/members/${uid}`).then((x) => x.data),
  changeRoomPassword: (roomId: string, new_password: string) =>
    client.patch(`${r(roomId)}/password`, { new_password }).then((x) => x.data),

  // ---- matches (room-scoped reads) ----
  matchDays: (roomId: string) =>
    client.get<MatchDay[]>(`${r(roomId)}/matches/days`).then((x) => x.data),
  matchesByDate: (roomId: string, date: string) =>
    client
      .get<Match[]>(`${r(roomId)}/matches`, { params: { date } })
      .then((x) => x.data),
  match: (roomId: string, id: string) =>
    client.get<Match>(`${r(roomId)}/matches/${id}`).then((x) => x.data),
  matchPredictions: (roomId: string, id: string) =>
    client
      .get<PlayerPrediction[]>(`${r(roomId)}/matches/${id}/predictions`)
      .then((x) => x.data),

  // ---- matches (global admin) ----
  adminMatches: () => client.get<Match[]>("/matches").then((x) => x.data),
  adminMatchesByDate: (date: string) =>
    client.get<Match[]>("/matches", { params: { date } }).then((x) => x.data),
  createMatch: (body: unknown) => client.post("/matches", body).then((x) => x.data),
  updateMatch: (id: string, body: unknown) =>
    client.patch(`/matches/${id}`, body).then((x) => x.data),
  setResult: (id: string, home: number, away: number) =>
    client
      .post(`/matches/${id}/result`, { home_score_ft: home, away_score_ft: away })
      .then((x) => x.data),
  setMatchMultiplier: (id: string, multiplier: number) =>
    client.patch(`/matches/${id}/multiplier`, { multiplier }).then((x) => x.data),
  setTourMultiplier: (date: string, multiplier: number) =>
    client
      .patch(`/matches/tour/${date}/multiplier`, { multiplier })
      .then((x) => x.data),

  // ---- predictions (room-scoped) ----
  batchPredict: (
    roomId: string,
    predictions: { match_id: string; home: number; away: number }[]
  ) =>
    client.post(`${r(roomId)}/predictions/batch`, { predictions }).then((x) => x.data),

  // ---- special (room-scoped) ----
  mySpecial: (roomId: string) =>
    client.get<SpecialPrediction>(`${r(roomId)}/special-prediction/my`).then((x) => x.data),
  updateSpecial: (
    roomId: string,
    body: {
      champion_team: string | null;
      top_scorer_name: string | null;
      top_scorer_api_id: number | null;
    }
  ) =>
    client
      .put<SpecialPrediction>(`${r(roomId)}/special-prediction`, body)
      .then((x) => x.data),
  allSpecial: (roomId: string) =>
    client.get(`${r(roomId)}/special-prediction/all`).then((x) => x.data),
  searchPlayers: (q: string) =>
    client.get("/players/search", { params: { q } }).then((x) => x.data),

  // ---- player profile (room-scoped) ----
  playerProfile: (roomId: string, userId: string) =>
    client.get<PlayerProfile>(`${r(roomId)}/players/${userId}`).then((x) => x.data),

  // ---- leaderboard (room-scoped) ----
  leaderboard: (roomId: string) =>
    client.get<LeaderboardEntry[]>(`${r(roomId)}/leaderboard`).then((x) => x.data),
  leaderboardMe: (roomId: string) =>
    client.get<LeaderboardEntry | null>(`${r(roomId)}/leaderboard/me`).then((x) => x.data),

  // ---- global admin ----
  sync: () => client.post("/admin/sync").then((x) => x.data),
  recalculate: () => client.post("/admin/recalculate").then((x) => x.data),
  scorerResult: (player_api_id: number, player_name: string) =>
    client.post("/admin/scorer-result", { player_api_id, player_name }).then((x) => x.data),
  transferSuperadmin: (target_user_id: string) =>
    client.post("/admin/superadmin/transfer", { target_user_id }).then((x) => x.data),
  auditLog: (params: { event_type?: string; limit?: number; offset?: number }) =>
    client.get<AuditEntry[]>("/admin/audit-log", { params }).then((x) => x.data),
  exportAuditLog: (params: { event_type?: string }) =>
    client
      .get("/admin/audit-log/export", { params, responseType: "blob" })
      .then((x) => x.data as Blob),
};
