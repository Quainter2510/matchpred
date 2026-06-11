import { create } from "zustand";

// Режим симуляции (только суперадмин): хранит симулированный момент времени.
// Пока он установлен, client.ts добавляет ко всем запросам заголовок
// X-Sim-Now, а utils/dates.ts считает «сейчас» от этого момента. Бэкенд
// отклоняет любые мутации с этим заголовком — режим строго read-only.
// Переживает перезагрузку страницы (localStorage), баннер всегда виден.

const KEY = "sim_now";

interface SimState {
  simNow: string | null; // ISO datetime (UTC) или null = режим выключен
  setSimNow: (iso: string | null) => void;
}

export const useSim = create<SimState>((set) => ({
  simNow: localStorage.getItem(KEY),
  setSimNow: (iso) => {
    if (iso) localStorage.setItem(KEY, iso);
    else localStorage.removeItem(KEY);
    set({ simNow: iso });
  },
}));

// Для не-React кода (axios interceptor, utils/dates).
export function getSimNow(): string | null {
  return useSim.getState().simNow;
}
