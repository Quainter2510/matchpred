import { create } from "zustand";

// Режим «как обычный пользователь» (только суперадмин): пока включён,
// client.ts шлёт заголовок X-View-As: player, и бэкенд в контексте комнат
// считает суперадмина обычным участником (чужие прогнозы скрыты до начала,
// управление комнатой недоступно). Глобальная панель остаётся доступной,
// чтобы можно было выключить режим. Переживает перезагрузку (localStorage).

const KEY = "view_as_player";

interface ViewAsState {
  asPlayer: boolean;
  setAsPlayer: (on: boolean) => void;
}

export const useViewAs = create<ViewAsState>((set) => ({
  asPlayer: localStorage.getItem(KEY) === "1",
  setAsPlayer: (on) => {
    if (on) localStorage.setItem(KEY, "1");
    else localStorage.removeItem(KEY);
    set({ asPlayer: on });
  },
}));

// Для не-React кода (axios interceptor).
export function getViewAsPlayer(): boolean {
  return useViewAs.getState().asPlayer;
}
