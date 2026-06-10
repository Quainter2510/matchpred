import { useRef, useState } from "react";
import { api } from "../api/endpoints";
import { useAuth } from "../store/auth";

export default function Profile() {
  const { user, setUser } = useAuth();
  const [nickname, setNickname] = useState(user?.nickname || "");
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState("");
  const [avatarBusy, setAvatarBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const [vk, setVk] = useState<{ code: string; bot_url: string | null } | null>(null);
  const [vkLoading, setVkLoading] = useState(false);
  const [showVkRelink, setShowVkRelink] = useState(false);

  const save = async () => {
    setErr("");
    setSaved(false);
    try {
      const me = await api.updateNickname(nickname);
      setUser(me);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e: any) {
      setErr(e.response?.data?.detail || "Ошибка");
    }
  };

  const onPickAvatar = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarBusy(true);
    try {
      const me = await api.uploadAvatar(file);
      setUser(me);
    } catch (e: any) {
      alert(e.response?.data?.detail || "Не удалось загрузить аватар");
    } finally {
      setAvatarBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const linkVk = async () => {
    setVkLoading(true);
    try {
      setVk(await api.vkLinkCode());
    } catch (e: any) {
      alert(e.response?.data?.detail || "Не удалось получить код");
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
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={avatarBusy}
            title="Сменить аватар"
            className="group relative h-20 w-20 shrink-0 overflow-hidden rounded-full"
          >
            {user?.avatar_url ? (
              <img src={user.avatar_url} className="h-20 w-20 rounded-full object-cover" />
            ) : (
              <div className="flex h-20 w-20 items-center justify-center rounded-full bg-slate-300 text-3xl">
                {user?.nickname?.[0]?.toUpperCase()}
              </div>
            )}
            <span className="absolute inset-0 flex items-center justify-center bg-black/40 text-xs text-white opacity-0 transition group-hover:opacity-100">
              {avatarBusy ? "…" : "Сменить"}
            </span>
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={onPickAvatar}
          />
          <div>
            <div className="font-semibold">{user?.nickname}</div>
            <div className="text-sm text-slate-500">{roleLabel}</div>
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              disabled={avatarBusy}
              className="mt-1 text-sm text-brand hover:underline disabled:opacity-50"
            >
              {avatarBusy ? "Загрузка…" : "Загрузить аватар"}
            </button>
          </div>
        </div>

        <div>
          <label className="text-sm text-slate-600">Никнейм</label>
          <div className="flex items-center gap-2">
            <input
              className="input"
              value={nickname}
              onChange={(e) => {
                setNickname(e.target.value);
                setSaved(false);
              }}
            />
            {saved && (
              <span className="flex shrink-0 items-center gap-1 text-sm font-medium text-emerald-600">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-xs text-white">
                  ✓
                </span>
                Изменён
              </span>
            )}
          </div>
        </div>
        {err && <p className="text-sm text-red-600">{err}</p>}
        <button className="btn-primary" onClick={save}>
          Сохранить
        </button>
      </div>

      <div className="card space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">ВКонтакте</h2>
          {user?.vk_linked && (
            <span className="flex items-center gap-1 text-sm font-medium text-emerald-600">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-xs text-white">
                ✓
              </span>
              Привязан
            </span>
          )}
        </div>

        {user?.vk_linked && !showVkRelink ? (
          <button
            type="button"
            onClick={() => setShowVkRelink(true)}
            className="text-sm text-slate-500 hover:underline"
          >
            Привязать другой аккаунт
          </button>
        ) : (
          <>
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
          </>
        )}
      </div>
    </div>
  );
}
