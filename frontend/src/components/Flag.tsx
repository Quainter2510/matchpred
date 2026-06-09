import { flagUrl } from "../utils/countries";

/** Флаг страны картинкой (flagcdn) — надёжнее эмодзи, которые не рисуются в Windows. */
export default function Flag({ code, title }: { code: string; title?: string }) {
  return (
    <img
      src={flagUrl(code, 20)}
      srcSet={`${flagUrl(code, 40)} 2x`}
      width={20}
      height={15}
      alt=""
      title={title}
      loading="lazy"
      className="inline-block h-[15px] w-5 shrink-0 rounded-[2px] object-cover"
    />
  );
}
