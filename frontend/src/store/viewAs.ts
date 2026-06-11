import { create } from "zustand";

// Суперадмин по умолчанию видит сайт как обычный игрок: client.ts шлёт
// заголовок X-View-As: player (бэкенд учитывает его только для суперадмина),
// и в контексте комнат чужие прогнозы скрыты до дедлайна, админ-кнопки
// спрятаны. «Режим суперадмина» включается чекбоксом в глобальной панели —
// тогда заголовок не шлётся, появляются полные права и баннер-уведомление.
// Глобальная панель доступна всегда. Состояние переживает перезагрузку.

const KEY = "admin_mode";

interface ViewAsState {
  adminMode: boolean;
  setAdminMode: (on: boolean) => void;
}

export const useViewAs = create<ViewAsState>((set) => ({
  adminMode: localStorage.getItem(KEY) === "1",
  setAdminMode: (on) => {
    if (on) localStorage.setItem(KEY, "1");
    else localStorage.removeItem(KEY);
    set({ adminMode: on });
  },
}));

// Для не-React кода (axios interceptor): true = слать X-View-As: player.
export function getViewAsPlayer(): boolean {
  return !useViewAs.getState().adminMode;
}
