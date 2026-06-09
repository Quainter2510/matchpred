import { useState } from "react";
import { api } from "../api/endpoints";
import { useAuth } from "../store/auth";

export default function Profile() {
  const { user, setUser } = useAuth();
  const [nickname, setNickname] = useState(user?.nickname || "");
  const [msg, setMsg] = useState("");

  const save = async () => {
    setMsg("");
    try {
      const me = await api.updateNickname(nickname);
      setUser(me);
      setMsg("Сохранено");
    } catch (err: any) {
      setMsg(err.response?.data?.detail || "Ошибка");
    }
  };

  const roleLabel =
    user?.system_role === "superadmin"
      ? "Суперадмин"
      : user?.tournament_role === "admin"
      ? "Админ турнира"
      : "Игрок";

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Профиль</h1>
      <div className="card space-y-4">
        <div className="flex items-center gap-3">
          {user?.avatar_url ? (
            <img src={user.avatar_url} className="h-16 w-16 rounded-full" />
          ) : (
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-300 text-2xl">
              {user?.nickname?.[0]?.toUpperCase()}
            </div>
          )}
          <div>
            <div className="font-semibold">{user?.nickname}</div>
            <div className="text-sm text-slate-500">{roleLabel}</div>
          </div>
        </div>

        <div>
          <label className="text-sm text-slate-600">Никнейм</label>
          <input
            className="input"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
          />
        </div>
        {msg && <p className="text-sm text-slate-600">{msg}</p>}
        <button className="btn-primary" onClick={save}>
          Сохранить
        </button>
      </div>
    </div>
  );
}
