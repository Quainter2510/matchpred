import { useEffect, useState } from "react";
import { api } from "../api/endpoints";

interface PlayerItem {
  api_id: number;
  name: string;
  team: string | null;
  photo: string | null;
}

interface Props {
  value: { id: number | null; name: string | null };
  onSelect: (id: number, name: string) => void;
  disabled?: boolean;
}

export default function PlayerSearch({ value, onSelect, disabled }: Props) {
  const [q, setQ] = useState(value.name || "");
  const [results, setResults] = useState<PlayerItem[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (q.length < 3 || disabled) {
      setResults([]);
      return;
    }
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const r = (await api.searchPlayers(q)) as PlayerItem[];
        setResults(r);
        setOpen(true);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 350);
    return () => clearTimeout(t);
  }, [q, disabled]);

  return (
    <div className="relative">
      <input
        className="input"
        placeholder="Имя бомбардира (мин. 3 символа)"
        value={q}
        disabled={disabled}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => results.length && setOpen(true)}
      />
      {loading && <div className="text-xs text-slate-400">Поиск…</div>}
      {open && results.length > 0 && (
        <div className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-lg border bg-white shadow">
          {results.map((p) => (
            <button
              key={p.api_id}
              className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-slate-100"
              onClick={() => {
                onSelect(p.api_id, p.name);
                setQ(p.name);
                setOpen(false);
              }}
            >
              {p.photo && <img src={p.photo} className="h-6 w-6 rounded-full" />}
              <span>{p.name}</span>
              {p.team && <span className="text-xs text-slate-400">{p.team}</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
