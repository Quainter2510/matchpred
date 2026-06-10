import { useState } from "react";
import { useAuth } from "../../store/auth";
import AdminMatches from "./AdminMatches";
import AdminSpecial from "./AdminSpecial";
import AdminSettings from "./AdminSettings";
import AdminAuditLog from "./AdminAuditLog";

type Tab = "matches" | "special" | "recalc" | "audit";

// Global admin panel: matches, results, scorer and recalculation are shared
// across all rooms. Members and room passwords are managed inside each room.
export default function Admin() {
  const isSuper = useAuth((s) => s.isSuperadmin());
  const [tab, setTab] = useState<Tab>("matches");

  const tabs: { id: Tab; label: string; super?: boolean }[] = [
    { id: "matches", label: "Матчи и результаты" },
    { id: "special", label: "Бомбардир" },
    { id: "recalc", label: "Пересчёт" },
    { id: "audit", label: "Журнал", super: true },
  ];

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Глобальная панель</h1>
      <p className="text-sm text-slate-500">
        Результаты матчей — общие для всех комнат. Управление участниками и
        паролем — внутри каждой комнаты.
      </p>
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
    </div>
  );
}
