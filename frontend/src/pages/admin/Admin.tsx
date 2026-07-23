import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../../store/auth";
import { useViewAs } from "../../store/viewAs";
import AdminMatches from "./AdminMatches";
import AdminSettings from "./AdminSettings";
import AdminAuditLog from "./AdminAuditLog";
import AdminSimulation from "./AdminSimulation";
import AdminTournaments from "./AdminTournaments";

type Tab = "tournaments" | "matches" | "recalc" | "audit" | "sim";

// Global admin panel (superadmin only): matches/results, recalculation, audit
// log and simulation are shared across all rooms. Per-room settings —
// multipliers, scorer, members, password — are managed inside each room.
export default function Admin() {
  const isSuper = useAuth((s) => s.isSuperadmin());
  const { adminMode, setAdminMode } = useViewAs();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("matches");

  const toggleAdminMode = (on: boolean) => {
    setAdminMode(on);
    queryClient.invalidateQueries();
  };

  const tabs: { id: Tab; label: string; super?: boolean }[] = [
    { id: "tournaments", label: "Турниры", super: true },
    { id: "matches", label: "Матчи и результаты" },
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

      {/* По умолчанию суперадмин ходит по сайту как обычный игрок. Полные
          права (чужие прогнозы до дедлайна, админ-кнопки в комнатах)
          включаются этим чекбоксом и сопровождаются баннером сверху. */}
      {isSuper && (
        <label className="flex w-fit cursor-pointer items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50/60 px-3 py-2 text-sm">
          <input
            type="checkbox"
            checked={adminMode}
            onChange={(e) => toggleAdminMode(e.target.checked)}
            className="h-4 w-4 accent-indigo-600"
          />
          <span>
            ⚙️ Режим суперадмина
            <span className="block text-xs text-slate-500">
              включить полные права в соревнованиях: чужие прогнозы до
              дедлайна, заполняемость туров, управление комнатами (по
              умолчанию вы видите сайт как обычный игрок)
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

      {tab === "tournaments" && isSuper && <AdminTournaments />}
      {tab === "matches" && <AdminMatches />}
      {tab === "recalc" && <AdminSettings />}
      {tab === "audit" && isSuper && <AdminAuditLog />}
      {tab === "sim" && isSuper && <AdminSimulation />}
    </div>
  );
}
