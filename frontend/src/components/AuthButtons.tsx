import { API_BASE } from "../api/client";
import { api } from "../api/endpoints";

const TG_BOT = import.meta.env.VITE_TELEGRAM_BOT;

// Кнопки OAuth-входа — общие для страницы /login и модалки авторизации.
export default function AuthButtons() {
  return (
    <div className="space-y-3">
      <a
        href={api.yandexLoginUrl()}
        className="btn block w-full bg-red-500 text-white hover:bg-red-600"
      >
        Войти через Яндекс
      </a>

      {TG_BOT ? (
        <a
          href={`${API_BASE}/auth/telegram/oauth-redirect`}
          className="btn block w-full bg-[#2AABEE] text-white hover:bg-[#1d96d4]"
        >
          Войти через Telegram
        </a>
      ) : (
        <p className="text-xs text-slate-400">
          Telegram-вход не настроен (VITE_TELEGRAM_BOT)
        </p>
      )}
    </div>
  );
}
