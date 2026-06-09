import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../../api/endpoints";

export default function AdminSettings() {
  const [pwd, setPwd] = useState("");

  const recalc = useMutation({
    mutationFn: api.recalculate,
    onSuccess: (r: any) => alert(`Пересчёт завершён: ${JSON.stringify(r)}`),
  });
  const changePwd = useMutation({
    mutationFn: () => api.changePassword(pwd),
    onSuccess: () => {
      alert("Пароль турнира обновлён");
      setPwd("");
    },
    onError: (e: any) => alert(e.response?.data?.detail || "Ошибка"),
  });

  return (
    <div className="space-y-6">
      <section className="card max-w-lg space-y-3">
        <h2 className="text-lg font-semibold">Пересчёт очков</h2>
        <p className="text-sm text-slate-500">
          Пересчитывает все незакрытые очки по завершённым матчам и победителю
          турнира (после ввода счёта финала). Операция идемпотентна.
        </p>
        <button
          className="btn-primary"
          onClick={() => recalc.mutate()}
          disabled={recalc.isPending}
        >
          {recalc.isPending ? "Пересчёт…" : "Пересчитать все очки"}
        </button>
      </section>

      <section className="card max-w-lg space-y-3">
        <h2 className="text-lg font-semibold">Пароль турнира</h2>
        <input
          type="text"
          className="input"
          placeholder="Новый пароль"
          value={pwd}
          onChange={(e) => setPwd(e.target.value)}
        />
        <button
          className="btn-primary"
          disabled={pwd.length < 4 || changePwd.isPending}
          onClick={() => changePwd.mutate()}
        >
          Сменить пароль
        </button>
      </section>
    </div>
  );
}
