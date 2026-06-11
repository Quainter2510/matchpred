export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    weekday: "short",
  });
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

import { getSimNow } from "../store/sim";

// «Сейчас» с учётом режима симуляции (для суперадмина): пока симуляция
// активна, отсчёт и блокировки на фронте считаются от симулированного момента.
export function nowMs(): number {
  const sim = getSimNow();
  return sim ? new Date(sim).getTime() : Date.now();
}

export function isPast(iso: string): boolean {
  return new Date(iso).getTime() <= nowMs();
}

export function countdown(iso: string): string {
  const diff = new Date(iso).getTime() - nowMs();
  if (diff <= 0) return "Приём завершён";
  const d = Math.floor(diff / 86400000);
  const h = Math.floor((diff % 86400000) / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  const s = Math.floor((diff % 60000) / 1000);
  if (d > 0) return `${d}д ${h}ч ${m}м`;
  return `${h.toString().padStart(2, "0")}:${m
    .toString()
    .padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}
