import { useState } from "react";
import { api } from "../api/endpoints";
import { useAuth } from "../store/auth";

export default function Profile() {
  const { user, setUser } = useAuth();
  const [nickname, setNickname] = useState(user?.nickname || "");
  const [msg, setMsg] = useState("");
  const [vk, setVk] = useState<{ code: string; bot_url: string | null } | null>(null);
  const [vkLoading, setVkLoading] = useState(false);

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

  const linkVk = async () => {
    setVkLoading(true);
    try {
      setVk(await api.vkLinkCode());
    } catch (err: any) {
      alert(err.response?.data?.detail || "Не удалось получить код");
    } finally {
      setVkLoading(false);
    }
  };

  const roleLabel =
    user?.system_role === "superadmin"
      ? "Суперадмин"
      : user?.is_any_admin
      ? "Админ соревнования"
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

      <div className="card space-y-3">
        <h2 className="text-lg font-semibold">Привязка ВКонтакте</h2>
        <p className="text-sm text-slate-500">
          Привяжите ВК, чтобы делать прогнозы через бота сообщества.
        </p>
        {!vk ? (
          <button className="btn-primary" onClick={linkVk} disabled={vkLoading}>
            {vkLoading ? "Готовим код…" : "Привязать ВК"}
          </button>
        ) : (
          <div className="space-y-2">
            <p className="text-sm">
              Откройте бота и пришлите ему этот код (действует 10 минут):
            </p>
            <div className="rounded-lg bg-slate-100 px-3 py-2 text-center text-2xl font-bold tracking-widest">
              {vk.code}
            </div>
            {vk.bot_url && (
              <a
                href={vk.bot_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn w-full bg-[#2787F5] text-white hover:bg-[#1b6fd6]"
              >
                Открыть бота ВК
              </a>
            )}
            <button className="btn-ghost w-full" onClick={linkVk} disabled={vkLoading}>
              Получить новый код
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
