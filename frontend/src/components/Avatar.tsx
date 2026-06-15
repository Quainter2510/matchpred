import { useEffect, useState } from "react";

/**
 * Аватар пользователя с устойчивым фолбэком: если картинка не загрузилась
 * (битая/просроченная ссылка — частый случай у Telegram-userpic, особенно на
 * мобильных), показываем кружок с первой буквой ника вместо «сломанного» изображения.
 *
 * referrerPolicy="no-referrer" помогает с хотлинк-защитой части провайдеров
 * (Telegram отдаёт userpic не всегда при наличии Referer).
 */
export default function Avatar({
  url,
  nick,
  className = "h-8 w-8",
  textClassName = "",
}: {
  url: string | null | undefined;
  nick: string;
  className?: string;
  textClassName?: string;
}) {
  const [failed, setFailed] = useState(false);
  // Сбрасываем флаг при смене ссылки (переиспользование инстанса в списках).
  useEffect(() => setFailed(false), [url]);

  if (url && !failed) {
    return (
      <img
        src={url}
        alt={nick}
        referrerPolicy="no-referrer"
        loading="lazy"
        onError={() => setFailed(true)}
        className={`${className} shrink-0 rounded-full object-cover`}
      />
    );
  }
  return (
    <div
      className={`${className} flex shrink-0 items-center justify-center rounded-full bg-slate-300 font-semibold text-slate-600 ${textClassName}`}
    >
      {nick?.[0]?.toUpperCase()}
    </div>
  );
}
