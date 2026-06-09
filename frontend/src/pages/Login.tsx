import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/endpoints";
import { setAccessToken } from "../api/client";
import { useAuth } from "../store/auth";

const TG_BOT = import.meta.env.VITE_TELEGRAM_BOT;

export default function Login() {
  const navigate = useNavigate();
  const loadMe = useAuth((s) => s.loadMe);
  const tgRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Telegram callback handler invoked by the widget.
    (window as any).onTelegramAuth = async (user: Record<string, unknown>) => {
      try {
        const res = await api.telegramVerify(user);
        setAccessToken(res.access_token);
        const me = await loadMe();
        if (res.is_new_user || !me?.nickname) navigate("/setup-profile");
        else if (!me?.tournament_role && me?.system_role !== "superadmin")
          navigate("/tournament-join");
        else navigate("/");
      } catch {
        alert("Ошибка входа через Telegram");
      }
    };

    if (TG_BOT && tgRef.current && !tgRef.current.hasChildNodes()) {
      const s = document.createElement("script");
      s.async = true;
      s.src = "https://telegram.org/js/telegram-widget.js?22";
      s.setAttribute("data-telegram-login", TG_BOT);
      s.setAttribute("data-size", "large");
      s.setAttribute("data-radius", "8");
      s.setAttribute("data-onauth", "onTelegramAuth(user)");
      s.setAttribute("data-request-access", "write");
      tgRef.current.appendChild(s);
    }
  }, [loadMe, navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="card w-full max-w-sm space-y-6 text-center">
        <div>
          <div className="text-3xl">⚽</div>
          <h1 className="mt-2 text-2xl font-bold">ЧМ-2026 · Прогнозы</h1>
          <p className="text-slate-500">Войдите, чтобы делать прогнозы</p>
        </div>

        <a href={api.yandexLoginUrl()} className="btn w-full bg-red-500 text-white hover:bg-red-600">
          Войти через Яндекс
        </a>

        <div className="flex justify-center" ref={tgRef}>
          {!TG_BOT && (
            <p className="text-xs text-slate-400">
              Telegram-вход не настроен (VITE_TELEGRAM_BOT)
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
