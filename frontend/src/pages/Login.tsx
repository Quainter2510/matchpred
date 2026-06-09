import { API_BASE } from "../api/client";
import { api } from "../api/endpoints";

const TG_BOT = import.meta.env.VITE_TELEGRAM_BOT;

export default function Login() {
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

        {TG_BOT ? (
          <a
            href={`${API_BASE}/auth/telegram/oauth-redirect`}
            className="btn w-full bg-[#2AABEE] text-white hover:bg-[#1d96d4]"
          >
            Войти через Telegram
          </a>
        ) : (
          <p className="text-xs text-slate-400">
            Telegram-вход не настроен (VITE_TELEGRAM_BOT)
          </p>
        )}
      </div>
    </div>
  );
}
