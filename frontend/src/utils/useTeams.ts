import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, TeamInfo } from "../api/endpoints";
import { findCountry } from "./countries";

// Карта команд «английское имя (lowercase) → {рус. имя, логотип}». Один запрос
// на всё приложение (react-query дедуплицирует по ключу), кэш почти вечный —
// справочник меняется редко.
export function useTeamsMap(): Map<string, TeamInfo> {
  const { data } = useQuery({
    queryKey: ["teams"],
    queryFn: api.teams,
    staleTime: 60 * 60_000,
  });
  return useMemo(() => {
    const m = new Map<string, TeamInfo>();
    for (const t of data || []) m.set(t.name_en.trim().toLowerCase(), t);
    return m;
  }, [data]);
}

// Функция «английское имя команды → отображаемое (русское) имя»: сборные из
// countries.ts, клубы из справочника, иначе — исходная строка.
export function useTeamName(): (name: string | null | undefined) => string {
  const map = useTeamsMap();
  return (name) => {
    if (!name) return "";
    const c = findCountry(name);
    if (c) return c.ru;
    return map.get(name.trim().toLowerCase())?.name_ru ?? name;
  };
}

// Логотип клуба по английскому имени (или null).
export function useTeamLogo(): (name: string | null | undefined) => string | null {
  const map = useTeamsMap();
  return (name) => (name ? map.get(name.trim().toLowerCase())?.logo ?? null : null);
}
