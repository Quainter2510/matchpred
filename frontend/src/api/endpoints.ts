import { client, API_BASE } from "./client";

export interface Me {
  id: string;
  nickname: string;
  avatar_url: string | null;
  system_role: "superadmin" | "user";
  tournament_role: "admin" | "player" | null;
}

export interface MatchDay {
  date: string;
  match_count: number;
  my_predictions_count: number;
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
  home_team: string;
  away_team: string;
  home_score_ft: number | null;
  away_score_ft: number | null;
  status: string;
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
}

export interface SpecialPrediction {
  champion_team: string | null;
  top_scorer_name: string | null;
  top_scorer_api_id: number | null;
  champion_points: number | null;
  scorer_points: number | null;
  locked: boolean;
}

export interface Member {
  user_id: string;
  nickname: string;
  avatar_url: string | null;
  system_role: string;
  tournament_role: string;
  total_points: number;
  exact_scores_count: number;
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

export const api = {
  // auth
  me: () => client.get<Me>("/auth/me").then((r) => r.data),
  updateNickname: (nickname: string) =>
    client.patch<Me>("/auth/me", { nickname }).then((r) => r.data),
  tournamentJoin: (password: string) =>
    client.post<Me>("/auth/tournament-join", { password }).then((r) => r.data),
  telegramVerify: (data: Record<string, unknown>) =>
    client.post<{ access_token: string; is_new_user: boolean }>(
      "/auth/telegram/verify",
      data
    ).then((r) => r.data),
  logout: () => client.post("/auth/logout"),
  yandexLoginUrl: () => `${API_BASE}/auth/yandex/login`,

  // matches
  matchDays: () => client.get<MatchDay[]>("/matches/days").then((r) => r.data),
  matchesByDate: (date: string) =>
    client.get<Match[]>("/matches", { params: { date } }).then((r) => r.data),
  match: (id: string) => client.get<Match>(`/matches/${id}`).then((r) => r.data),
  matchPredictions: (id: string) =>
    client.get<PlayerPrediction[]>(`/matches/${id}/predictions`).then((r) => r.data),
  createMatch: (body: unknown) => client.post("/matches", body).then((r) => r.data),
  updateMatch: (id: string, body: unknown) =>
    client.patch(`/matches/${id}`, body).then((r) => r.data),
  setResult: (id: string, home: number, away: number) =>
    client.post(`/matches/${id}/result`, {
      home_score_ft: home,
      away_score_ft: away,
    }).then((r) => r.data),

  // predictions
  batchPredict: (
    predictions: { match_id: string; home: number; away: number }[]
  ) => client.post("/predictions/batch", { predictions }).then((r) => r.data),

  // special
  mySpecial: () =>
    client.get<SpecialPrediction>("/special-prediction/my").then((r) => r.data),
  updateSpecial: (body: {
    champion_team: string | null;
    top_scorer_name: string | null;
    top_scorer_api_id: number | null;
  }) => client.put<SpecialPrediction>("/special-prediction", body).then((r) => r.data),
  allSpecial: () => client.get("/special-prediction/all").then((r) => r.data),
  searchPlayers: (q: string) =>
    client.get("/players/search", { params: { q } }).then((r) => r.data),

  // leaderboard
  leaderboard: () =>
    client.get<LeaderboardEntry[]>("/leaderboard").then((r) => r.data),
  leaderboardMe: () =>
    client.get<LeaderboardEntry | null>("/leaderboard/me").then((r) => r.data),

  // admin
  members: () => client.get<Member[]>("/admin/members").then((r) => r.data),
  changeRole: (uid: string, role: string) =>
    client.patch(`/admin/members/${uid}/role`, { role }).then((r) => r.data),
  removeMember: (uid: string) =>
    client.delete(`/admin/members/${uid}`).then((r) => r.data),
  changePassword: (new_password: string) =>
    client.patch("/tournament/password", { new_password }).then((r) => r.data),
  sync: () => client.post("/admin/sync").then((r) => r.data),
  recalculate: () => client.post("/admin/recalculate").then((r) => r.data),
  scorerResult: (player_api_id: number, player_name: string) =>
    client.post("/admin/scorer-result", { player_api_id, player_name }).then((r) => r.data),
  transferSuperadmin: (target_user_id: string) =>
    client.post("/admin/superadmin/transfer", { target_user_id }).then((r) => r.data),
  auditLog: (params: { event_type?: string; limit?: number; offset?: number }) =>
    client.get<AuditEntry[]>("/admin/audit-log", { params }).then((r) => r.data),
};
