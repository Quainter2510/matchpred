import { useQueryClient } from "@tanstack/react-query";
import { useViewAs } from "../store/viewAs";
import { useAuth } from "../store/auth";

// Полоса режима «как обычный пользователь» (только суперадмин). Кнопка выхода
// всегда под рукой — даже если админ-ссылки в этом режиме спрятаны.
export default function ViewAsBanner() {
  const isSuper = useAuth((s) => s.isSuperadmin());
  const { asPlayer, setAsPlayer } = useViewAs();
  const queryClient = useQueryClient();

  if (!isSuper || !asPlayer) return null;

  return (
    <div className="sticky top-0 z-50 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 bg-indigo-500 px-4 py-2 text-sm font-medium text-white shadow">
      <span>👤 Режим обычного пользователя — админ-возможности скрыты</span>
      <button
        onClick={() => {
          setAsPlayer(false);
          queryClient.invalidateQueries();
        }}
        className="rounded border border-indigo-200 px-2 py-0.5 text-xs font-semibold hover:bg-indigo-400"
      >
        Вернуть права суперадмина
      </button>
    </div>
  );
}
