import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../../store/auth";
import { useViewAs } from "../../store/viewAs";
import AdminMatches from "./AdminMatches";
import AdminSpecial from "./AdminSpecial";
import AdminSettings from "./AdminSettings";
import AdminAuditLog from "./AdminAuditLog";
import AdminSimulation from "./AdminSimulation";

type Tab = "matches" | "special" | "recalc" | "audit" | "sim";

// Global admin panel: matches, results, scorer and recalculation are shared
// across all rooms. Members and room passwords are managed inside each room.
export default function Admin() {
  const isSuper = useAuth((s) => s.isSuperadmin());
  const { asPlayer, setAsPlayer } = useViewAs();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("matches");

  const toggleViewAs = (on: boolean) => {
    setAsPlayer(on);
    queryClient.invalidateQueries();
  };

  const tabs: { id: Tab; label: string; super?: boolean }[] = [
    { id: "matches", label: "Матчи и результаты" },
    { id: "special", label: "Бомбардир" },
    { id: "recalc", label: "Пересчёт" },
    { id: "audit", label: "Журнал", super: true },
    { id: "sim", label: "Симуляция", super: true },
  ];

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Глобальная панель</h1>
      <p className="text-sm text-slate-500">
        Результаты матчей — общие для всех соревнований. Управление участниками
        и паролем — внутри каждого соревнования.
      </p>

      {/* Режим обычного пользователя: суперадмин ходит по сайту как игрок —
          чужие прогнозы скрыты до начала, админ-кнопки спрятаны. */}
      {isSuper && (
        <label className="flex w-fit cursor-pointer items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50/60 px-3 py-2 text-sm">
          <input
            type="checkbox"
            checked={asPlayer}
            onChange={(e) => toggleViewAs(e.target.checked)}
            className="h-4 w-4 accent-indigo-600"
          />
          <span>
            👤 Режим обычного пользователя
            <span className="block text-xs text-slate-500">
              видеть сайт как игрок: без чужих прогнозов до дедлайна и без
              админ-кнопок (выключается здесь же или в баннере сверху)
            </span>
          </span>
        </label>
      )}
      <div className="flex flex-wrap gap-2 border-b">
        {tabs
          .filter((t) => !t.super || isSuper)
          .map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-3 py-2 ${
                tab === t.id
                  ? "border-b-2 border-brand font-semibold text-brand"
                  : "text-slate-500"
              }`}
            >
              {t.label}
            </button>
          ))}
      </div>

      {tab === "matches" && <AdminMatches />}
      {tab === "special" && <AdminSpecial />}
      {tab === "recalc" && <AdminSettings />}
      {tab === "audit" && isSuper && <AdminAuditLog />}
      {tab === "sim" && isSuper && <AdminSimulation />}
    </div>
  );
}
