import { useState } from "react";
import { useAuth } from "../../store/auth";
import AdminMatches from "./AdminMatches";
import AdminMembers from "./AdminMembers";
import AdminSpecial from "./AdminSpecial";
import AdminSettings from "./AdminSettings";
import AdminAuditLog from "./AdminAuditLog";

type Tab = "matches" | "members" | "special" | "settings" | "audit";

export default function Admin() {
  const isSuper = useAuth((s) => s.isSuperadmin());
  const [tab, setTab] = useState<Tab>("matches");

  const tabs: { id: Tab; label: string; super?: boolean }[] = [
    { id: "matches", label: "Матчи" },
    { id: "members", label: "Участники" },
    { id: "special", label: "Спецпрогнозы" },
    { id: "settings", label: "Пересчёт / Пароль" },
    { id: "audit", label: "Журнал", super: true },
  ];

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Панель администратора</h1>
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
      {tab === "members" && <AdminMembers />}
      {tab === "special" && <AdminSpecial />}
      {tab === "settings" && <AdminSettings />}
      {tab === "audit" && isSuper && <AdminAuditLog />}
    </div>
  );
}
