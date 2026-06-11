import { useQueryClient } from "@tanstack/react-query";
import { useViewAs } from "../store/viewAs";
import { useAuth } from "../store/auth";

// Уведомление о включённом режиме суперадмина. По умолчанию суперадмин видит
// сайт как обычный игрок (баннера нет); баннер появляется только при
// включённых полных правах и позволяет быстро вернуться в режим игрока.
export default function ViewAsBanner() {
  const isSuper = useAuth((s) => s.isSuperadmin());
  const { adminMode, setAdminMode } = useViewAs();
  const queryClient = useQueryClient();

  if (!isSuper || !adminMode) return null;

  return (
    <div className="sticky top-0 z-50 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 bg-indigo-500 px-4 py-2 text-sm font-medium text-white shadow">
      <span>⚙️ Режим суперадмина включён — видны чужие прогнозы и админ-кнопки</span>
      <button
        onClick={() => {
          setAdminMode(false);
          queryClient.invalidateQueries();
        }}
        className="rounded border border-indigo-200 px-2 py-0.5 text-xs font-semibold hover:bg-indigo-400"
      >
        Вернуться в режим игрока
      </button>
    </div>
  );
}
