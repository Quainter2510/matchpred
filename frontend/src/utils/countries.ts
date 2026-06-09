// Маппинг названий сборных (англ. из API-Football) → русское название + код страны.
// Хранится и сравнивается на бэкенде по-прежнему английское каноническое имя,
// поэтому UI переводит только для отображения и выбора.
// Флаг рисуется картинкой по ISO-коду (эмодзи-флаги не отображаются в Windows).

export interface Country {
  en: string; // каноническое имя (как приходит из API-Football)
  ru: string;
  code: string; // ISO 3166-1 alpha-2 (или gb-eng/gb-sct/gb-wls/gb-nir) для flagcdn
  aliases?: string[]; // альтернативные написания из API
}

export const COUNTRIES: Country[] = [
  { en: "Brazil", ru: "Бразилия", code: "br" },
  { en: "Argentina", ru: "Аргентина", code: "ar" },
  { en: "France", ru: "Франция", code: "fr" },
  { en: "England", ru: "Англия", code: "gb-eng" },
  { en: "Spain", ru: "Испания", code: "es" },
  { en: "Germany", ru: "Германия", code: "de" },
  { en: "Portugal", ru: "Португалия", code: "pt" },
  { en: "Netherlands", ru: "Нидерланды", code: "nl" },
  { en: "Belgium", ru: "Бельгия", code: "be" },
  { en: "Italy", ru: "Италия", code: "it" },
  { en: "Croatia", ru: "Хорватия", code: "hr" },
  { en: "Uruguay", ru: "Уругвай", code: "uy" },
  { en: "Colombia", ru: "Колумбия", code: "co" },
  { en: "Mexico", ru: "Мексика", code: "mx" },
  { en: "USA", ru: "США", code: "us", aliases: ["United States", "United States of America"] },
  { en: "Canada", ru: "Канада", code: "ca" },
  { en: "Japan", ru: "Япония", code: "jp" },
  { en: "South Korea", ru: "Южная Корея", code: "kr", aliases: ["Korea Republic"] },
  { en: "Australia", ru: "Австралия", code: "au" },
  { en: "Morocco", ru: "Марокко", code: "ma" },
  { en: "Senegal", ru: "Сенегал", code: "sn" },
  { en: "Ghana", ru: "Гана", code: "gh" },
  { en: "Nigeria", ru: "Нигерия", code: "ng" },
  { en: "Cameroon", ru: "Камерун", code: "cm" },
  { en: "Egypt", ru: "Египет", code: "eg" },
  { en: "Algeria", ru: "Алжир", code: "dz" },
  { en: "Tunisia", ru: "Тунис", code: "tn" },
  { en: "Ivory Coast", ru: "Кот-д’Ивуар", code: "ci", aliases: ["Côte d'Ivoire", "Cote d'Ivoire"] },
  { en: "Switzerland", ru: "Швейцария", code: "ch" },
  { en: "Denmark", ru: "Дания", code: "dk" },
  { en: "Sweden", ru: "Швеция", code: "se" },
  { en: "Poland", ru: "Польша", code: "pl" },
  { en: "Serbia", ru: "Сербия", code: "rs" },
  { en: "Wales", ru: "Уэльс", code: "gb-wls" },
  { en: "Scotland", ru: "Шотландия", code: "gb-sct" },
  { en: "Austria", ru: "Австрия", code: "at" },
  { en: "Ukraine", ru: "Украина", code: "ua" },
  { en: "Czech Republic", ru: "Чехия", code: "cz", aliases: ["Czechia"] },
  { en: "Turkey", ru: "Турция", code: "tr", aliases: ["Türkiye", "Turkiye"] },
  { en: "Greece", ru: "Греция", code: "gr" },
  { en: "Norway", ru: "Норвегия", code: "no" },
  { en: "Hungary", ru: "Венгрия", code: "hu" },
  { en: "Russia", ru: "Россия", code: "ru" },
  { en: "Iran", ru: "Иран", code: "ir", aliases: ["IR Iran"] },
  { en: "Saudi Arabia", ru: "Саудовская Аравия", code: "sa" },
  { en: "Qatar", ru: "Катар", code: "qa" },
  { en: "Iraq", ru: "Ирак", code: "iq" },
  { en: "UAE", ru: "ОАЭ", code: "ae", aliases: ["United Arab Emirates"] },
  { en: "Ecuador", ru: "Эквадор", code: "ec" },
  { en: "Peru", ru: "Перу", code: "pe" },
  { en: "Chile", ru: "Чили", code: "cl" },
  { en: "Paraguay", ru: "Парагвай", code: "py" },
  { en: "Bolivia", ru: "Боливия", code: "bo" },
  { en: "Venezuela", ru: "Венесуэла", code: "ve" },
  { en: "Costa Rica", ru: "Коста-Рика", code: "cr" },
  { en: "Panama", ru: "Панама", code: "pa" },
  { en: "Jamaica", ru: "Ямайка", code: "jm" },
  { en: "Honduras", ru: "Гондурас", code: "hn" },
  { en: "New Zealand", ru: "Новая Зеландия", code: "nz" },
  { en: "Mali", ru: "Мали", code: "ml" },
  { en: "Burkina Faso", ru: "Буркина-Фасо", code: "bf" },
  { en: "DR Congo", ru: "ДР Конго", code: "cd", aliases: ["Congo DR", "Democratic Republic of the Congo"] },
  { en: "South Africa", ru: "ЮАР", code: "za" },
  { en: "Cape Verde", ru: "Кабо-Верде", code: "cv", aliases: ["Cabo Verde"] },
  { en: "Gabon", ru: "Габон", code: "ga" },
  { en: "Guinea", ru: "Гвинея", code: "gn" },
  { en: "Angola", ru: "Ангола", code: "ao" },
  { en: "Zambia", ru: "Замбия", code: "zm" },
  { en: "Uzbekistan", ru: "Узбекистан", code: "uz" },
  { en: "Jordan", ru: "Иордания", code: "jo" },
  { en: "Oman", ru: "Оман", code: "om" },
  { en: "China", ru: "Китай", code: "cn", aliases: ["China PR"] },
  { en: "India", ru: "Индия", code: "in" },
  { en: "Slovenia", ru: "Словения", code: "si" },
  { en: "Slovakia", ru: "Словакия", code: "sk" },
  { en: "Romania", ru: "Румыния", code: "ro" },
  { en: "Bulgaria", ru: "Болгария", code: "bg" },
  { en: "Finland", ru: "Финляндия", code: "fi" },
  { en: "Iceland", ru: "Исландия", code: "is" },
  { en: "Republic of Ireland", ru: "Ирландия", code: "ie", aliases: ["Ireland"] },
  { en: "Northern Ireland", ru: "Северная Ирландия", code: "gb-nir" },
  { en: "Bosnia and Herzegovina", ru: "Босния и Герцеговина", code: "ba", aliases: ["Bosnia"] },
  { en: "Albania", ru: "Албания", code: "al" },
  { en: "North Macedonia", ru: "Северная Македония", code: "mk" },
  { en: "Montenegro", ru: "Черногория", code: "me" },
  { en: "Georgia", ru: "Грузия", code: "ge" },
  { en: "Israel", ru: "Израиль", code: "il" },
  { en: "Kazakhstan", ru: "Казахстан", code: "kz" },
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

/** URL картинки флага (flagcdn) по ISO-коду. */
export function flagUrl(code: string, w: 20 | 40 = 20): string {
  return `https://flagcdn.com/w${w}/${code}.png`;
}
