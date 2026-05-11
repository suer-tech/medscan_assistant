import { TemplateField } from "@/components/TemplateFormFields";

/**
 * Поля шаблона протокола сопровождения ОСТ-снимка (макулярная область / задний полюс)
 * По умолчанию все поля включены в запрос к ИИ
 */
export const DEFAULT_TEMPLATE_FIELDS: TemplateField[] = [
  // I. Техническая часть
  {
    name: "Модель ОСТ",
    value: "",
    included: true,
  },
  {
    name: "Режим сканирования",
    value: "",
    included: true,
  },
  {
    name: "Область сканирования (поле)",
    value: "",
    included: true,
  },
  {
    name: "Количество срезов / плотность raster",
    value: "",
    included: true,
  },
  {
    name: "Усреднение",
    value: "",
    included: true,
  },
  {
    name: "Индекс качества (Signal Strength Index / Quality Index)",
    value: "",
    included: true,
  },
  {
    name: "Отмеченные артефакты",
    value: "",
    included: true,
  },
  {
    name: "Номер центрального среза",
    value: "",
    included: true,
  },
  {
    name: "Центральная толщина сетчатки (CST)",
    value: "",
    included: true,
  },
  {
    name: "Карта ETDRS приложена",
    value: "",
    included: true,
  },
  {
    name: "Особые зоны утолщения / истончения",
    value: "",
    included: true,
  },
  {
    name: "Сторона глаза",
    value: "",
    included: true,
  },
  {
    name: "Фокус",
    value: "",
    included: true,
  },
  {
    name: "Контакт линзы / качество фиксации",
    value: "",
    included: true,
  },
  {
    name: "Другие технические особенности",
    value: "",
    included: true,
  },
  
  // II. Описание структуры сетчатки
  {
    name: "Оптические среды (роговица, хрусталик, стекловидное тело)",
    value: "",
    included: true,
  },
  {
    name: "Контур фовеальной ямки, профиль",
    value: "",
    included: true,
  },
  {
    name: "Наличие/отсутствие субретинальной жидкости",
    value: "",
    included: true,
  },
  {
    name: "Наличие/отсутствие внутрисетчаточной жидкости, кист (ИРФ)",
    value: "",
    included: true,
  },
  {
    name: "Наличие/отсутствие отслойки нейроэпителия",
    value: "",
    included: true,
  },
  {
    name: "Слоистость сетчатки (ILM, RNFL, GCL, INL, OPL, ONL, IS/OS, RPE)",
    value: "",
    included: true,
  },
  {
    name: "Пигментный эпителий сетчатки (RPE) и хориокапилляры",
    value: "",
    included: true,
  },
  {
    name: "Задняя гиалоидная мембрана / витреомакулярный интерфейс",
    value: "",
    included: true,
  },
  {
    name: "Прочие структурные особенности",
    value: "",
    included: true,
  },
  
  // III. Анализ паттернов
  {
    name: "Профиль макулы и фовеальной ямки",
    value: "",
    included: true,
  },
  {
    name: "Характер жидкости",
    value: "",
    included: true,
  },
  {
    name: "Описание жидкости",
    value: "",
    included: true,
  },
  {
    name: "Изменения витреомакулярного интерфейса (VMT, ЭРМ, ПВД и др.)",
    value: "",
    included: true,
  },
  {
    name: "Состояние RPE и наружных слоёв (IS/OS, эллипсоидная зона и др.)",
    value: "",
    included: true,
  },
  {
    name: "Толщинный паттерн по карте ETDRS",
    value: "",
    included: true,
  },
  {
    name: "Предполагаемый паттерн заболевания",
    value: "",
    included: true,
  },
  
  // IV. Заключение
  {
    name: "Основные ОСТ-признаки",
    value: "",
    included: true,
  },
  {
    name: "Предварительная интерпретация / клиническое заключение по ОСТ",
    value: "",
    included: true,
  },
  {
    name: "Необходимость динамического наблюдения / контрольного ОСТ",
    value: "",
    included: true,
  },
  {
    name: "Необходимость сопоставления с ОКТ-ангиографией / ФАГ / клиническими данными",
    value: "",
    included: true,
  },
  {
    name: "Консультация специалиста (ретинолог и др.)",
    value: "",
    included: true,
  },
  {
    name: "Иные рекомендации",
    value: "",
    included: true,
  },
];





