import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/endpoints";

const EVENT_TYPES = [
  "",
  "user_registered",
  "superadmin_assigned",
  "superadmin_transferred",
  "role_changed",
  "member_removed",
  "match_result_set",
  "scores_recalculated",
  "scorer_result_set",
  "tournament_password_changed",
  "api_sync",
  "nickname_changed",
];

const PAGE = 50;

export default function AdminAuditLog() {
  const [eventType, setEventType] = useState("");
  const [offset, setOffset] = useState(0);

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
              {t || "Все события"}
            </option>
          ))}
        </select>
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
                  <td>
                    <code className="text-xs">{e.event_type}</code>
                  </td>
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
