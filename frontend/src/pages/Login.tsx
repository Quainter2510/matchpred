import AuthButtons from "../components/AuthButtons";

// Коды ошибок входа, с которыми бэкенд редиректит на /login?error=…
const AUTH_ERRORS: Record<string, string> = {
  yandex_expired: "Сессия входа через Яндекс истекла. Попробуйте ещё раз.",
  yandex_denied: "Вход через Яндекс отменён.",
  yandex_unavailable:
    "Яндекс не ответил или отклонил запрос. Попробуйте позже или войдите другим способом.",
  yandex_failed:
    "Не удалось войти через Яндекс. Попробуйте позже или войдите другим способом.",
  telegram_auth_failed: "Не удалось войти через Telegram. Попробуйте ещё раз.",
};

export default function Login() {
  const code = new URLSearchParams(window.location.search).get("error");
  const error = code ? AUTH_ERRORS[code] || "Не удалось войти." : null;

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="card w-full max-w-sm space-y-6 text-center">
        <div>
          <div className="text-3xl">⚽</div>
          <h1 className="mt-2 text-2xl font-bold">ЧМ-2026 · Прогнозы</h1>
          <p className="text-slate-500">Войдите, чтобы делать прогнозы</p>
        </div>
        {error && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        <AuthButtons />
      </div>
    </div>
  );
}
