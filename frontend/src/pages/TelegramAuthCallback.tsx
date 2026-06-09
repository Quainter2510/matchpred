import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/endpoints";
import { setAccessToken } from "../api/client";
import { useAuth } from "../store/auth";

export default function TelegramAuthCallback() {
  const navigate = useNavigate();
  const loadMe = useAuth((s) => s.loadMe);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    const error = params.get("error");

    // Legacy redirect-mode flow (backend callback) — kept as fallback
    if (error) {
      navigate("/login?error=telegram_auth_failed", { replace: true });
      return;
    }
    if (token) {
      setAccessToken(token);
      loadMe().then((me) => {
        if (!me?.nickname) navigate("/setup-profile", { replace: true });
        else if (!me?.tournament_role && me?.system_role !== "superadmin")
          navigate("/tournament-join", { replace: true });
        else navigate("/", { replace: true });
      });
      return;
    }

    // oauth.telegram.org redirect mode — data arrives as #tgAuthResult=BASE64
    const hash = window.location.hash;
    const match = hash.match(/[#&]tgAuthResult=([A-Za-z0-9+/=_-]+)/);
    if (!match) {
      navigate("/login?error=telegram_auth_failed", { replace: true });
      return;
    }

    let authData: Record<string, unknown>;
    try {
      // tgAuthResult is base64url-encoded JSON
      const base64 = match[1].replace(/-/g, "+").replace(/_/g, "/");
      authData = JSON.parse(atob(base64));
    } catch {
      navigate("/login?error=telegram_auth_failed", { replace: true });
      return;
    }

    api.telegramVerify(authData).then((res) => {
      setAccessToken(res.access_token);
      return loadMe().then((me) => {
        if (res.is_new_user || !me?.nickname)
          navigate("/setup-profile", { replace: true });
        else if (!me?.tournament_role && me?.system_role !== "superadmin")
          navigate("/tournament-join", { replace: true });
        else navigate("/", { replace: true });
      });
    }).catch(() => {
      navigate("/login?error=telegram_auth_failed", { replace: true });
    });
  }, [loadMe, navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-slate-500">Вход через Telegram…</p>
    </div>
  );
}
