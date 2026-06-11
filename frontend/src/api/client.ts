import axios from "axios";
import { getSimNow } from "../store/sim";

export const API_BASE =
  import.meta.env.VITE_API_BASE || "http://localhost:8000/api/v1";

export const client = axios.create({
  baseURL: API_BASE,
  withCredentials: true, // send refresh cookie
});

let accessToken: string | null = localStorage.getItem("access_token");

export function setAccessToken(token: string | null) {
  accessToken = token;
  if (token) localStorage.setItem("access_token", token);
  else localStorage.removeItem("access_token");
}

export function getAccessToken() {
  return accessToken;
}

client.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  // Режим симуляции: заголовок ставится на все запросы, включая мутации —
  // бэкенд отклоняет мутации с ним (403), чтобы из «песочницы» нельзя было
  // случайно изменить реальные данные. Авторизация (refresh/logout) должна
  // работать и в симуляции, поэтому /auth не трогаем.
  const simNow = getSimNow();
  if (simNow && !(config.url || "").startsWith("/auth")) {
    config.headers["X-Sim-Now"] = simNow;
  }
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function doRefresh(): Promise<string | null> {
  try {
    const resp = await axios.post(
      `${API_BASE}/auth/refresh`,
      {},
      { withCredentials: true }
    );
    const token = resp.data.access_token as string;
    setAccessToken(token);
    return token;
  } catch {
    setAccessToken(null);
    return null;
  }
}

client.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    const url: string = original?.url || "";
    // Don't attempt refresh for the pre-auth endpoints (refresh itself, login,
    // telegram verify) — only for normal API calls and /auth/me.
    const skipRefresh =
      url.includes("/auth/refresh") ||
      url.includes("/auth/login") ||
      url.includes("/auth/telegram");
    if (error.response?.status === 401 && !original._retry && !skipRefresh) {
      original._retry = true;
      refreshing = refreshing || doRefresh();
      const token = await refreshing;
      refreshing = null;
      if (token) {
        original.headers.Authorization = `Bearer ${token}`;
        return client(original);
      }
      // Refresh failed. Bounce to login only from a protected page — never from
      // a public auth page, otherwise the anonymous initial load loops.
      const publicPaths = [
        "/",
        "/rooms",
        "/login",
        "/auth/callback",
        "/telegram-auth",
        "/setup-profile",
      ];
      if (!publicPaths.includes(window.location.pathname)) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
