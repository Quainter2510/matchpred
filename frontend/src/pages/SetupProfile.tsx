import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/endpoints";
import { useAuth } from "../store/auth";

export default function SetupProfile() {
  const [nickname, setNickname] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const setUser = useAuth((s) => s.setUser);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (nickname.length < 3 || nickname.length > 24) {
      setError("Никнейм должен быть 3–24 символа");
      return;
    }
    try {
      const me = await api.updateNickname(nickname);
      setUser(me);
      if (me.system_role === "superadmin") navigate("/");
      else navigate("/tournament-join");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Не удалось сохранить никнейм");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4">
        <h1 className="text-xl font-bold">Выберите никнейм</h1>
        <input
          className="input"
          placeholder="3–24 символа"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          autoFocus
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button className="btn-primary w-full">Продолжить</button>
      </form>
    </div>
  );
}
