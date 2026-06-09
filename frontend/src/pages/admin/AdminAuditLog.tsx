import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/endpoints";

const EVENT_LABELS: Record<string, string> = {
  user_registered: "Регистрация",
  superadmin_assigned: "Назначен суперадмин",
  superadmin_transferred: "Передана роль суперадмина",
  role_changed: "Изменена роль",
  member_removed: "Удалён участник",
  match_result_set: "Добавлен счёт",
  match_result_updated: "Изменён счёт",
  scores_recalculated: "Пересчёт очков",
  scorer_result_set: "Итоговый бомбардир (начисление)",
  champion_selected: "Выбран чемпион",
  top_scorer_selected: "Выбран бомбардир",
  tournament_password_changed: "Смена пароля турнира",
  api_sync: "Синхронизация с API",
  nickname_changed: "Смена никнейма",
};

const EVENT_TYPES = ["", ...Object.keys(EVENT_LABELS)];

const PAGE = 50;

export default function AdminAuditLog() {
  const [eventType, setEventType] = useState("");
  const [offset, setOffset] = useState(0);
  const [exporting, setExporting] = useState(false);

  const exportCsv = async () => {
    setExporting(true);
    try {
      const blob = await api.exportAuditLog({
        event_type: eventType || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Не удалось выгрузить журнал");
    } finally {
      setExporting(false);
    }
  };

  const { data, isLoading } = useQuery({
    queryKey: ["audit", eventType, offset],
    queryFn: () =>
      api.auditLog({
        event_type: eventType || undefined,
        limit: PAGE,
        offset,
      }),
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <select
          className="input w-auto"
          value={eventType}
          onChange={(e) => {
            setEventType(e.target.value);
            setOffset(0);
          }}
        >
          {EVENT_TYPES.map((t) => (
            <option key={t} value={t}>
              {t ? EVENT_LABELS[t] ?? t : "Все события"}
            </option>
          ))}
        </select>
        <button
          className="btn-ghost"
          onClick={exportCsv}
          disabled={exporting}
        >
          {exporting ? "Выгрузка…" : "Скачать CSV"}
        </button>
      </div>

      <div className="card overflow-x-auto">
        {isLoading ? (
          <p className="text-slate-500">Загрузка…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-slate-500">
                <th className="py-2">Время</th>
                <th>Инициатор</th>
                <th>Событие</th>
                <th>Детали</th>
              </tr>
            </thead>
            <tbody>
              {(data || []).map((e) => (
                <tr key={e.id} className="border-b align-top">
                  <td className="py-2 whitespace-nowrap text-xs text-slate-500">
                    {new Date(e.created_at).toLocaleString("ru-RU")}
                  </td>
                  <td>{e.actor_nickname || "система"}</td>
                  <td>{EVENT_LABELS[e.event_type] ?? e.event_type}</td>
                  <td className="text-xs text-slate-500">
                    {e.details ? JSON.stringify(e.details) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="flex justify-between">
        <button
          className="btn-ghost"
          disabled={offset === 0}
          onClick={() => setOffset(Math.max(0, offset - PAGE))}
        >
          ← Назад
        </button>
        <button
          className="btn-ghost"
          disabled={(data?.length || 0) < PAGE}
          onClick={() => setOffset(offset + PAGE)}
        >
          Вперёд →
        </button>
      </div>
    </div>
  );
}
