// Маппинг названий сборных (англ. из API-Football) → русское название + флаг.
// Хранится и сравнивается на бэкенде по-прежнему английское каноническое имя,
// поэтому UI переводит только для отображения и выбора.

export interface Country {
  en: string; // каноническое имя (как приходит из API-Football)
  ru: string;
  flag: string;
  aliases?: string[]; // альтернативные написания из API
}

export const COUNTRIES: Country[] = [
  { en: "Brazil", ru: "Бразилия", flag: "🇧🇷" },
  { en: "Argentina", ru: "Аргентина", flag: "🇦🇷" },
  { en: "France", ru: "Франция", flag: "🇫🇷" },
  { en: "England", ru: "Англия", flag: "🏴󠁧󠁢󠁥󠁮󠁧󠁿" },
  { en: "Spain", ru: "Испания", flag: "🇪🇸" },
  { en: "Germany", ru: "Германия", flag: "🇩🇪" },
  { en: "Portugal", ru: "Португалия", flag: "🇵🇹" },
  { en: "Netherlands", ru: "Нидерланды", flag: "🇳🇱" },
  { en: "Belgium", ru: "Бельгия", flag: "🇧🇪" },
  { en: "Italy", ru: "Италия", flag: "🇮🇹" },
  { en: "Croatia", ru: "Хорватия", flag: "🇭🇷" },
  { en: "Uruguay", ru: "Уругвай", flag: "🇺🇾" },
  { en: "Colombia", ru: "Колумбия", flag: "🇨🇴" },
  { en: "Mexico", ru: "Мексика", flag: "🇲🇽" },
  { en: "USA", ru: "США", flag: "🇺🇸", aliases: ["United States", "United States of America"] },
  { en: "Canada", ru: "Канада", flag: "🇨🇦" },
  { en: "Japan", ru: "Япония", flag: "🇯🇵" },
  { en: "South Korea", ru: "Южная Корея", flag: "🇰🇷", aliases: ["Korea Republic"] },
  { en: "Australia", ru: "Австралия", flag: "🇦🇺" },
  { en: "Morocco", ru: "Марокко", flag: "🇲🇦" },
  { en: "Senegal", ru: "Сенегал", flag: "🇸🇳" },
  { en: "Ghana", ru: "Гана", flag: "🇬🇭" },
  { en: "Nigeria", ru: "Нигерия", flag: "🇳🇬" },
  { en: "Cameroon", ru: "Камерун", flag: "🇨🇲" },
  { en: "Egypt", ru: "Египет", flag: "🇪🇬" },
  { en: "Algeria", ru: "Алжир", flag: "🇩🇿" },
  { en: "Tunisia", ru: "Тунис", flag: "🇹🇳" },
  { en: "Ivory Coast", ru: "Кот-д’Ивуар", flag: "🇨🇮", aliases: ["Côte d'Ivoire", "Cote d'Ivoire"] },
  { en: "Switzerland", ru: "Швейцария", flag: "🇨🇭" },
  { en: "Denmark", ru: "Дания", flag: "🇩🇰" },
  { en: "Sweden", ru: "Швеция", flag: "🇸🇪" },
  { en: "Poland", ru: "Польша", flag: "🇵🇱" },
  { en: "Serbia", ru: "Сербия", flag: "🇷🇸" },
  { en: "Wales", ru: "Уэльс", flag: "🏴󠁧󠁢󠁷󠁬󠁳󠁿" },
  { en: "Scotland", ru: "Шотландия", flag: "🏴󠁧󠁢󠁳󠁣󠁴󠁿" },
  { en: "Austria", ru: "Австрия", flag: "🇦🇹" },
  { en: "Ukraine", ru: "Украина", flag: "🇺🇦" },
  { en: "Czech Republic", ru: "Чехия", flag: "🇨🇿", aliases: ["Czechia"] },
  { en: "Turkey", ru: "Турция", flag: "🇹🇷", aliases: ["Türkiye", "Turkiye"] },
  { en: "Greece", ru: "Греция", flag: "🇬🇷" },
  { en: "Norway", ru: "Норвегия", flag: "🇳🇴" },
  { en: "Hungary", ru: "Венгрия", flag: "🇭🇺" },
  { en: "Russia", ru: "Россия", flag: "🇷🇺" },
  { en: "Iran", ru: "Иран", flag: "🇮🇷", aliases: ["IR Iran"] },
  { en: "Saudi Arabia", ru: "Саудовская Аравия", flag: "🇸🇦" },
  { en: "Qatar", ru: "Катар", flag: "🇶🇦" },
  { en: "Iraq", ru: "Ирак", flag: "🇮🇶" },
  { en: "UAE", ru: "ОАЭ", flag: "🇦🇪", aliases: ["United Arab Emirates"] },
  { en: "Ecuador", ru: "Эквадор", flag: "🇪🇨" },
  { en: "Peru", ru: "Перу", flag: "🇵🇪" },
  { en: "Chile", ru: "Чили", flag: "🇨🇱" },
  { en: "Paraguay", ru: "Парагвай", flag: "🇵🇾" },
  { en: "Bolivia", ru: "Боливия", flag: "🇧🇴" },
  { en: "Venezuela", ru: "Венесуэла", flag: "🇻🇪" },
  { en: "Costa Rica", ru: "Коста-Рика", flag: "🇨🇷" },
  { en: "Panama", ru: "Панама", flag: "🇵🇦" },
  { en: "Jamaica", ru: "Ямайка", flag: "🇯🇲" },
  { en: "Honduras", ru: "Гондурас", flag: "🇭🇳" },
  { en: "New Zealand", ru: "Новая Зеландия", flag: "🇳🇿" },
  { en: "Mali", ru: "Мали", flag: "🇲🇱" },
  { en: "Burkina Faso", ru: "Буркина-Фасо", flag: "🇧🇫" },
  { en: "DR Congo", ru: "ДР Конго", flag: "🇨🇩", aliases: ["Congo DR", "Democratic Republic of the Congo"] },
  { en: "South Africa", ru: "ЮАР", flag: "🇿🇦" },
  { en: "Cape Verde", ru: "Кабо-Верде", flag: "🇨🇻", aliases: ["Cabo Verde"] },
  { en: "Gabon", ru: "Габон", flag: "🇬🇦" },
  { en: "Guinea", ru: "Гвинея", flag: "🇬🇳" },
  { en: "Angola", ru: "Ангола", flag: "🇦🇴" },
  { en: "Zambia", ru: "Замбия", flag: "🇿🇲" },
  { en: "Uzbekistan", ru: "Узбекистан", flag: "🇺🇿" },
  { en: "Jordan", ru: "Иордания", flag: "🇯🇴" },
  { en: "Oman", ru: "Оман", flag: "🇴🇲" },
  { en: "China", ru: "Китай", flag: "🇨🇳", aliases: ["China PR"] },
  { en: "India", ru: "Индия", flag: "🇮🇳" },
  { en: "Slovenia", ru: "Словения", flag: "🇸🇮" },
  { en: "Slovakia", ru: "Словакия", flag: "🇸🇰" },
  { en: "Romania", ru: "Румыния", flag: "🇷🇴" },
  { en: "Bulgaria", ru: "Болгария", flag: "🇧🇬" },
  { en: "Finland", ru: "Финляндия", flag: "🇫🇮" },
  { en: "Iceland", ru: "Исландия", flag: "🇮🇸" },
  { en: "Republic of Ireland", ru: "Ирландия", flag: "🇮🇪", aliases: ["Ireland"] },
  { en: "Northern Ireland", ru: "Северная Ирландия", flag: "🏴󠁧󠁢󠁮󠁩󠁲󠁿" },
  { en: "Bosnia and Herzegovina", ru: "Босния и Герцеговина", flag: "🇧🇦", aliases: ["Bosnia"] },
  { en: "Albania", ru: "Албания", flag: "🇦🇱" },
  { en: "North Macedonia", ru: "Северная Македония", flag: "🇲🇰" },
  { en: "Montenegro", ru: "Черногория", flag: "🇲🇪" },
  { en: "Georgia", ru: "Грузия", flag: "🇬🇪" },
  { en: "Israel", ru: "Израиль", flag: "🇮🇱" },
  { en: "Kazakhstan", ru: "Казахстан", flag: "🇰🇿" },
];

const _byKey = new Map<string, Country>();
for (const c of COUNTRIES) {
  _byKey.set(c.en.toLowerCase(), c);
  _byKey.set(c.ru.toLowerCase(), c);
  for (const a of c.aliases || []) _byKey.set(a.toLowerCase(), c);
}

/** Найти страну по английскому/русскому имени или алиасу. */
export function findCountry(name: string | null | undefined): Country | undefined {
  if (!name) return undefined;
  return _byKey.get(name.trim().toLowerCase());
}

/** Русское название сборной (фолбэк — исходное имя). */
export function teamRu(name: string | null | undefined): string {
  if (!name) return "";
  return findCountry(name)?.ru ?? name;
}

/** Флаг сборной (фолбэк — пустая строка). */
export function teamFlag(name: string | null | undefined): string {
  return findCountry(name)?.flag ?? "";
}

/** "🇧🇷 Бразилия" — флаг + русское название одной строкой. */
export function teamLabel(name: string | null | undefined): string {
  if (!name) return "";
  const c = findCountry(name);
  return c ? `${c.flag} ${c.ru}` : name;
}
