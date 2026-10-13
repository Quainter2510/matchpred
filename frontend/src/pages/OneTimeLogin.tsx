import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/endpoints";
import { setAccessToken } from "../api/client";
import { useAuth } from "../store/auth";

// Вход по одноразовой ссылке от суперадмина: /auth/one-time#token=…
// Токен лежит во fragment и обменивается на сессию POST-запросом.
export default function OneTimeLogin() {
  const navigate = useNavigate();
  const loadMe = useAuth((s) => s.loadMe);
  const [error, setError] = useState<string | null>(null);
  // Токен одноразовый — повторный запуск эффекта не должен слать его дважды.
  const sent = useRef(false);

  useEffect(() => {
    if (sent.current) return;
    sent.current = true;
    const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
    // Убираем токен из адресной строки и истории браузера.
    window.history.replaceState({}, "", "/auth/one-time");
    if (!token) {
      setError("Ссылка недействительна.");
      return;
    }
    api
      .oneTimeLogin(token)
      .then((res) => {
        setAccessToken(res.access_token);
        return loadMe().then((me) => {
          if (!me?.nickname) navigate("/setup-profile", { replace: true });
          else navigate("/", { replace: true });
        });
      })
      .catch((e: any) =>
        setError(
          e.response?.data?.detail ||
            "Ссылка недействительна, уже использована или истекла."
        )
      );
  }, [loadMe, navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      {error ? (
        <div className="card w-full max-w-sm space-y-3 text-center">
          <p className="text-red-700">{error}</p>
          <p className="text-sm text-slate-500">
            Попросите администратора выдать новую ссылку.
          </p>
          <Link to="/login" className="btn-ghost inline-block">
            На страницу входа
          </Link>
        </div>
      ) : (
        <p className="text-slate-500">Входим…</p>
      )}
    </div>
  );
}
