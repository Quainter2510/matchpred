import AuthButtons from "../components/AuthButtons";

export default function Login() {
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="card w-full max-w-sm space-y-6 text-center">
        <div>
          <div className="text-3xl">⚽</div>
          <h1 className="mt-2 text-2xl font-bold">ЧМ-2026 · Прогнозы</h1>
          <p className="text-slate-500">Войдите, чтобы делать прогнозы</p>
        </div>
        <AuthButtons />
      </div>
    </div>
  );
}
