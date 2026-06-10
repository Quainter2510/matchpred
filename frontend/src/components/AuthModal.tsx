import AuthButtons from "./AuthButtons";

// Окно авторизации: появляется, когда анонимный пользователь пытается
// выполнить действие (войти в соревнование и т.п.).
export default function AuthModal({ onClose }: { onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="card w-full max-w-sm space-y-6 text-center"
        onClick={(e) => e.stopPropagation()}
      >
        <div>
          <div className="text-3xl">⚽</div>
          <h2 className="mt-2 text-xl font-bold">Нужно войти</h2>
          <p className="text-slate-500">
            Авторизуйтесь, чтобы участвовать в соревнованиях
          </p>
        </div>
        <AuthButtons />
        <button className="text-sm text-slate-400 hover:underline" onClick={onClose}>
          Не сейчас
        </button>
      </div>
    </div>
  );
}
