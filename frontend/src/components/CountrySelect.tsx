import { useEffect, useRef, useState } from "react";
import { COUNTRIES, findCountry } from "../utils/countries";
import Flag from "./Flag";

interface Props {
  /** Хранимое каноническое (английское) имя сборной или "". */
  value: string;
  onChange: (en: string) => void;
  disabled?: boolean;
  /** Подсветить поле зелёным (выбор сохранён). */
  highlight?: boolean;
}

/** Автодополнение со списком сборных: подсказки на русском + флаг.
 *  Наружу отдаёт английское каноническое имя (для совпадения при подсчёте). */
export default function CountrySelect({ value, onChange, disabled, highlight }: Props) {
  const selected = findCountry(value);
  const [q, setQ] = useState(selected?.ru ?? value ?? "");
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  // Синхронизация при загрузке сохранённого значения.
  useEffect(() => {
    const c = findCountry(value);
    setQ(c?.ru ?? value ?? "");
  }, [value]);

  // Закрытие по клику вне компонента.
  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const term = q.trim().toLowerCase();
  const matches = term
    ? COUNTRIES.filter(
        (c) =>
          c.ru.toLowerCase().includes(term) ||
          c.en.toLowerCase().includes(term)
      )
    : COUNTRIES;

  return (
    <div className="relative" ref={boxRef}>
      <input
        className={`input ${highlight ? "bg-emerald-50 ring-2 ring-emerald-500" : ""}`}
        placeholder="Начните вводить страну…"
        value={q}
        disabled={disabled}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
          // Сброс выбора, пока не выбрана точная страна.
          if (findCountry(e.target.value)?.en !== value) onChange("");
        }}
        onFocus={() => !disabled && setOpen(true)}
      />
      {open && !disabled && matches.length > 0 && (
        <div className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-lg border bg-white shadow">
          {matches.map((c) => (
            <button
              key={c.en}
              type="button"
              className={`flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-slate-100 ${
                c.en === value ? "bg-blue-50 font-medium" : ""
              }`}
              onClick={() => {
                onChange(c.en);
                setQ(c.ru);
                setOpen(false);
              }}
            >
              <Flag code={c.code} title={c.ru} />
              <span>{c.ru}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
