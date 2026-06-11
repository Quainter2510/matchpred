import { useQueryClient } from "@tanstack/react-query";
import { useSim } from "../store/sim";
import { useAuth } from "../store/auth";

// Полоса-предупреждение режима симуляции (только суперадмин). Видна на всех
// экранах, пока симуляция активна; выход сбрасывает кэш запросов, чтобы
// мгновенно вернуться к реальным данным.
export default function SimBanner() {
  const isSuper = useAuth((s) => s.isSuperadmin());
  const { simNow, setSimNow } = useSim();
  const queryClient = useQueryClient();

  if (!isSuper || !simNow) return null;

  const formatted = new Date(simNow).toLocaleString("ru-RU", {
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="sticky top-0 z-50 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 bg-amber-400 px-4 py-2 text-sm font-medium text-amber-950 shadow">
      <span>
        ⚠ Режим симуляции: <b>{formatted}</b> — счета и очки не настоящие,
        изменения заблокированы
      </span>
      <button
        onClick={() => {
          setSimNow(null);
          queryClient.invalidateQueries();
        }}
        className="rounded border border-amber-700 px-2 py-0.5 text-xs font-semibold hover:bg-amber-300"
      >
        Выйти из симуляции
      </button>
    </div>
  );
}
