import { useMutation } from "@tanstack/react-query";
import { api } from "../../api/endpoints";

// Global recalculation. A match result scores every room at once, so this is a
// global operation. (Room passwords are managed per-room in the room admin.)
export default function AdminSettings() {
  const recalc = useMutation({
    mutationFn: api.recalculate,
    onSuccess: (r: any) => alert(`Пересчёт завершён: ${JSON.stringify(r)}`),
  });

  return (
    <div className="space-y-6">
      <section className="card max-w-lg space-y-3">
        <h2 className="text-lg font-semibold">Пересчёт очков</h2>
        <p className="text-sm text-slate-500">
          Пересчитывает все незакрытые очки по завершённым матчам и победителю
          турнира (после ввода счёта финала) — во всех комнатах. Операция
          идемпотентна.
        </p>
        <button
          className="btn-primary"
          onClick={() => recalc.mutate()}
          disabled={recalc.isPending}
        >
          {recalc.isPending ? "Пересчёт…" : "Пересчитать все очки"}
        </button>
      </section>
    </div>
  );
}
