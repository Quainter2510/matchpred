import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { setAccessToken } from "../api/client";
import { useAuth } from "../store/auth";

// Yandex OAuth redirects here with #access_token=...&is_new_user=...
export default function AuthCallback() {
  const navigate = useNavigate();
  const loadMe = useAuth((s) => s.loadMe);

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.slice(1));
    const token = params.get("access_token");
    const isNew = params.get("is_new_user") === "true";
    if (!token) {
      navigate("/login");
      return;
    }
    setAccessToken(token);
    loadMe().then((me) => {
      if (isNew) navigate("/setup-profile");
      else if (!me?.tournament_role && me?.system_role !== "superadmin")
        navigate("/tournament-join");
      else navigate("/");
    });
  }, [loadMe, navigate]);

  return <div className="p-8 text-slate-500">Входим…</div>;
}
