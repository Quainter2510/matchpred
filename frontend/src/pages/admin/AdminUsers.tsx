import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AdminUser, api } from "../../api/endpoints";
import Avatar from "../../components/Avatar";

const PROVIDER_LABELS: Record<string, string> = {
  yandex: "Яндекс",
  telegram: "Telegram",
  vk: "VK",
};

// Что выдано пользователю и нужно передать ему лично.
type Issued =
  | { kind: "login"; user: AdminUser; url: string; minutes: number }
  | {
      kind: "vk";
      user: AdminUser;
      code: string;
      botUrl: string | null;
      minutes: number;
      alreadyLinked: boolean;
    };

function CopyRow({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* буфер недоступен — текст можно выделить вручную */
    }
  };
  return (
    <div className="flex items-center gap-2">
      <input
        readOnly
        className="input font-mono text-xs"
        value={value}
        onFocus={(e) => e.target.select()}
      />
      <button className="btn-ghost shrink-0" onClick={copy}>
        {copied ? "Скопировано" : "Скопировать"}
      </button>
    </div>
  );
}

// Пользователи (только суперадмин): запасной вход по одноразовой ссылке и код
// привязки VK-бота, которые админ передаёт человеку лично.
export default function AdminUsers() {
  const [q, setQ] = useState("");
  const [issued, setIssued] = useState<Issued | null>(null);
  const users = useQuery({
    queryKey: ["admin-users", q],
    queryFn: () => api.adminUsers(q.trim() || undefined),
  });

  const onError = (e: any) => alert(e.response?.data?.detail || "Ошибка");
  const loginLink = useMutation({
    mutationFn: (u: AdminUser) =>
      api.adminLoginLink(u.id).then((r) => ({ u, r })),
    onSuccess: ({ u, r }) =>
      setIssued({
        kind: "login",
        user: u,
        url: r.url,
        minutes: Math.round(r.expires_in / 60),
      }),
    onError,
  });
  const vkCode = useMutation({
    mutationFn: (u: AdminUser) =>
      api.adminVkLinkCode(u.id).then((r) => ({ u, r })),
    onSuccess: ({ u, r }) =>
      setIssued({
        kind: "vk",
        user: u,
        code: r.code,
        botUrl: r.bot_url,
        minutes: Math.round(r.expires_in / 60),
        alreadyLinked: r.already_linked,
      }),
    onError,
  });
  const busy = loginLink.isPending || vkCode.isPending;

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">
        Одноразовая ссылка входа пускает в аккаунт без Яндекса и Telegram, код
        VK привязывает бота к аккаунту. И то и другое передавайте только лично
        владельцу аккаунта — кто получил ссылку, тот и войдёт.
      </p>

      {issued && (
        <section className="card space-y-2 border border-indigo-200 bg-indigo-50/60">
          <div className="flex items-start justify-between gap-2">
            <h2 className="font-semibold">
              {issued.kind === "login"
                ? `Ссылка входа для ${issued.user.nickname}`
                : `Код привязки VK для ${issued.user.nickname}`}
            </h2>
            <button
              className="text-slate-400 hover:text-slate-600"
              title="Скрыть"
              onClick={() => setIssued(null)}
            >
              ✕
            </button>
          </div>
          {issued.kind === "login" ? (
            <>
              <CopyRow value={issued.url} />
              <p className="text-xs text-slate-500">
                Действует {issued.minutes} мин и только один раз. Показана
                единственный раз — после закрытия получить её снова нельзя,
                только выдать новую.
              </p>
            </>
          ) : (
            <>
              <CopyRow value={issued.code} />
              <p className="text-xs text-slate-500">
                Пользователь отправляет этот код сообщением боту сообщества
                {issued.botUrl ? (
                  <>
                    {" "}
                    (<span className="font-mono">{issued.botUrl}</span>)
                  </>
                ) : null}
                . Действует {issued.minutes} мин, одноразовый.
              </p>
              {issued.alreadyLinked && (
                <p className="text-xs text-amber-700">
                  У пользователя уже привязан VK — код привяжет ещё один
                  VK-аккаунт.
                </p>
              )}
            </>
          )}
        </section>
      )}

      <input
        className="input max-w-sm"
        placeholder="Поиск по никнейму"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />

      <div className="card overflow-x-auto">
        {users.isLoading ? (
          <p className="text-slate-500">Загрузка…</p>
        ) : !users.data?.length ? (
          <p className="text-slate-500">Пользователи не найдены.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-slate-500">
                <th className="py-2">Пользователь</th>
                <th>Вход через</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {users.data.map((u) => (
                <tr key={u.id} className="border-b">
                  <td className="py-2">
                    <span className="flex items-center gap-2">
                      <Avatar
                        url={u.avatar_url}
                        nick={u.nickname}
                        className="h-6 w-6"
                        textClassName="text-xs"
                      />
                      {u.nickname}
                      {u.system_role === "superadmin" && (
                        <span className="text-xs font-semibold text-brand">
                          суперадмин
                        </span>
                      )}
                      {!u.is_active && (
                        <span className="text-xs text-slate-400">отключён</span>
                      )}
                    </span>
                  </td>
                  <td className="text-xs text-slate-600">
                    {u.providers.length
                      ? u.providers.map((p) => PROVIDER_LABELS[p] ?? p).join(", ")
                      : "—"}
                  </td>
                  <td className="space-x-3 whitespace-nowrap text-right">
                    <button
                      className="text-xs text-brand hover:underline disabled:text-slate-300"
                      disabled={busy || !u.is_active}
                      onClick={() => loginLink.mutate(u)}
                    >
                      Ссылка входа
                    </button>
                    <button
                      className="text-xs text-brand hover:underline disabled:text-slate-300"
                      disabled={busy || !u.is_active}
                      onClick={() => vkCode.mutate(u)}
                    >
                      Код VK
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
