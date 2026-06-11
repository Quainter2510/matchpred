import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/endpoints";
import { useSim } from "../../store/sim";
import { formatDate, formatTime } from "../../utils/dates";

// Сколько добавить к началу последнего матча дня, чтобы считать тур
// «завершённым» (матч идёт ~2 часа).
const MATCH_DURATION_MS = 3 * 3600000;

interface Preset {
  id: string;
  label: string;
  detail: string;
  iso: string;
}

// Вкладка «Симуляция» (только суперадмин): выбрать момент времени и
// посмотреть, как будут выглядеть все экраны — матчи без реального счёта
// получают детерминированный фейковый, очки пересчитываются на лету.
// Ничего не записывается; мутации в режиме симуляции бэкенд отклоняет.
export default function AdminSimulation() {
  const { simNow, setSimNow } = useSim();
  const queryClient = useQueryClient();
  const [custom, setCustom] = useState("");

  const { data: matches, isLoading } = useQuery({
    queryKey: ["admin-matches-all"],
    queryFn: api.adminMatches,
  });

  const presets = useMemo<Preset[]>(() => {
    if (!matches || matches.length === 0) return [];
    const byDay = new Map<string, number>(); // date -> последний kickoff (ms)
    let firstKickoff = Infinity;
    for (const m of matches) {
      const t = new Date(m.kickoff_at).getTime();
      firstKickoff = Math.min(firstKickoff, t);
      byDay.set(m.match_date, Math.max(byDay.get(m.match_date) ?? 0, t));
    }
    const days = [...byDay.entries()].sort(([a], [b]) => a.localeCompare(b));
    const out: Preset[] = [
      {
        id: "first-started",
        label: "Первый матч начался",
        detail: "через 5 минут после стартового свистка",
        iso: new Date(firstKickoff + 5 * 60000).toISOString(),
      },
    ];
    days.forEach(([date, lastKickoff], i) => {
      out.push({
        id: `tour-${date}`,
        label: `Тур ${i + 1} завершён (${formatDate(date)})`,
        detail: "все матчи дня сыграны",
        iso: new Date(lastKickoff + MATCH_DURATION_MS).toISOString(),
      });
    });
    const last = days[days.length - 1];
    out.push({
      id: "all-finished",
      label: "Турнир завершён",
      detail: "после последнего матча расписания",
      iso: new Date(last[1] + MATCH_DURATION_MS).toISOString(),
    });
    return out;
  }, [matches]);

  const activate = (iso: string) => {
    setSimNow(iso);
    queryClient.invalidateQueries();
  };
  const deactivate = () => {
    setSimNow(null);
    queryClient.invalidateQueries();
  };

  const tourPresets = presets.filter((p) => p.id.startsWith("tour-"));
  const otherPresets = presets.filter((p) => !p.id.startsWith("tour-"));

  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-white p-4 text-sm text-slate-600">
        <p>
          Режим симуляции показывает, как будут выглядеть экраны системы в
          выбранный момент времени: начавшиеся к этому моменту матчи считаются
          завершёнными (без реального счёта подставляется фейковый), очки и
          таблицы пересчитываются на лету по правилам каждого соревнования.
        </p>
        <p className="mt-2">
          Ничего не записывается — это просмотр. Любые изменения (прогнозы,
          результаты) в режиме симуляции заблокированы. Очки за чемпиона и
          бомбардира не симулируются.
        </p>
      </div>

      {simNow && (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-amber-300 bg-amber-50 p-4">
          <span className="text-sm">
            Сейчас симулируется:{" "}
            <b>
              {formatDate(simNow)}, {formatTime(simNow)}
            </b>
          </span>
          <button
            onClick={deactivate}
            className="rounded bg-amber-500 px-3 py-1 text-sm font-semibold text-white hover:bg-amber-600"
          >
            Выйти из симуляции
          </button>
        </div>
      )}

      <div className="rounded-lg border bg-white p-4">
        <h2 className="mb-3 font-semibold">Сценарии</h2>
        {isLoading && <div className="text-sm text-slate-500">Загрузка…</div>}
        {!isLoading && presets.length === 0 && (
          <div className="text-sm text-slate-500">
            Матчи ещё не загружены — добавьте их на вкладке «Матчи и
            результаты» или укажите время вручную ниже.
          </div>
        )}
        <div className="flex flex-col gap-2">
          {otherPresets.map((p) => (
            <PresetButton key={p.id} preset={p} active={simNow === p.iso} onClick={activate} />
          ))}
        </div>
        {tourPresets.length > 0 && (
          <div className="mt-3">
            <div className="mb-1 text-sm font-medium text-slate-600">После тура:</div>
            <div className="grid gap-2 sm:grid-cols-2">
              {tourPresets.map((p) => (
                <PresetButton key={p.id} preset={p} active={simNow === p.iso} onClick={activate} />
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="rounded-lg border bg-white p-4">
        <h2 className="mb-3 font-semibold">Произвольный момент</h2>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="datetime-local"
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            className="rounded border px-2 py-1 text-sm"
          />
          <button
            disabled={!custom}
            onClick={() => activate(new Date(custom).toISOString())}
            className="rounded bg-brand px-3 py-1 text-sm font-semibold text-white disabled:opacity-50"
          >
            Включить
          </button>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Время указывается в вашем часовом поясе.
        </p>
      </div>
    </div>
  );
}

function PresetButton({
  preset,
  active,
  onClick,
}: {
  preset: Preset;
  active: boolean;
  onClick: (iso: string) => void;
}) {
  return (
    <button
      onClick={() => onClick(preset.iso)}
      className={`rounded border px-3 py-2 text-left text-sm hover:bg-slate-50 ${
        active ? "border-amber-400 bg-amber-50" : ""
      }`}
    >
      <div className="font-medium">{preset.label}</div>
      <div className="text-xs text-slate-500">
        {preset.detail} · {formatDate(preset.iso)}, {formatTime(preset.iso)}
      </div>
    </button>
  );
}
