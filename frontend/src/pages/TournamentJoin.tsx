import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/endpoints";
import { useAuth } from "../store/auth";

export default function TournamentJoin() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const setUser = useAuth((s) => s.setUser);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const me = await api.tournamentJoin(password);
      setUser(me);
      navigate("/");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Неверный пароль");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4">
        <h1 className="text-xl font-bold">Пароль турнира</h1>
        <p className="text-sm text-slate-500">
          Пароль выдаёт организатор турнира.
        </p>
        <input
          type="password"
          className="input"
          placeholder="Пароль"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button className="btn-primary w-full">Войти в турнир</button>
      </form>
    </div>
  );
}
