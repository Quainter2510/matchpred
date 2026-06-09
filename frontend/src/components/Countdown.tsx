import { useEffect, useState } from "react";
import { countdown } from "../utils/dates";

export default function Countdown({ to }: { to: string }) {
  const [text, setText] = useState(countdown(to));
  useEffect(() => {
    const id = setInterval(() => setText(countdown(to)), 1000);
    return () => clearInterval(id);
  }, [to]);
  const done = text === "Приём завершён";
  return (
    <span className={done ? "text-red-600" : "text-emerald-600"}>{text}</span>
  );
}
