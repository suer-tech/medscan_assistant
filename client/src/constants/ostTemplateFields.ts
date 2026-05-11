import { TemplateField } from "@/components/TemplateFormFields";

/**
 * Справочники для полей формы ОСТ-снимка
 */
export const OCT_MODELS = [
  "Zeiss Cirrus",
  "Heidelberg Spectralis",
  "Topcon DRI OCT Triton",
  "Nidek RS-3000",
  "Optovue iVue",
  "Canon OCT-HS100",
  "Другое",
];

export const SCAN_MODES = [
  "Line Scan",
  "Raster Scan",
  "Radial Scan",
  "Circle Scan",
  "Volume Scan",
  "3D Scan",
  "Enhanced Depth Imaging (EDI)",
  "Другое",
];

/**
 * Поля шаблона протокола сопровождения ОСТ-снимка (макулярная область / задний полюс)
 * Реорганизованы согласно новой структуре
 */
export const DEFAULT_TEMPLATE_FIELDS: TemplateField[] = [
  // ========== ВХОДНЫЕ ДАННЫЕ ==========
  
  // Параметры прибора (0-2)
  {
    name: "Название прибора",
    value: "",
    included: true,
  },
  {
    name: "Модель ОСТ",
    value: "",
    included: true,
    fieldType: "select",
    options: OCT_MODELS,
  },
  {
    name: "Режим сканирования",
    value: "",
    included: true,
    fieldType: "select",
    options: SCAN_MODES,
  },
  
  // Параметры сканирования (3-8)
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
  
  // Параметры изображения (9-12)
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
  
  // Комментарии оператора исследования (13-15)
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
  
  // ========== ОПИСАНИЕ СТРУКТУРЫ СЕТЧАТКИ И АНАЛИЗ ПАТТЕРНОВ ==========
  // Поля 16-31 (две колонки: врач слева, ИИ справа)
  {
    name: "Оптические среды (роговица, хрусталик, стекловидное тело)",
    value: "",
    included: true,
    section: "structure",
  },
  {
    name: "Контур фовеальной ямки, профиль",
    value: "",
    included: true,
    section: "structure",
  },
  {
    name: "Наличие/отсутствие субретинальной жидкости",
    value: "",
    included: true,
    section: "structure",
  },
  {
    name: "Наличие/отсутствие внутрисетчаточной жидкости, кист (ИРФ)",
    value: "",
    included: true,
    section: "structure",
  },
  {
    name: "Наличие/отсутствие отслойки нейроэпителия",
    value: "",
    included: true,
    section: "structure",
  },
  {
    name: "Слоистость сетчатки (ILM, RNFL, GCL, INL, OPL, ONL, IS/OS, RPE)",
    value: "",
    included: true,
    section: "structure",
  },
  {
    name: "Пигментный эпителий сетчатки (RPE) и хориокапилляры",
    value: "",
    included: true,
    section: "structure",
  },
  {
    name: "Задняя гиалоидная мембрана / витреомакулярный интерфейс",
    value: "",
    included: true,
    section: "structure",
  },
  {
    name: "Прочие структурные особенности",
    value: "",
    included: true,
    section: "structure",
  },
  {
    name: "Профиль макулы и фовеальной ямки",
    value: "",
    included: true,
    section: "structure",
  },
  {
    name: "Характер жидкости",
    value: "",
    included: true,
    section: "structure",
  },
  {
    name: "Описание жидкости",
    value: "",
    included: true,
    section: "structure",
  },
  {
    name: "Изменения витреомакулярного интерфейса (VMT, ЭРМ, ПВД и др.)",
    value: "",
    included: true,
    section: "structure",
  },
  {
    name: "Состояние RPE и наружных слоёв (IS/OS, эллипсоидная зона и др.)",
    value: "",
    included: true,
    section: "structure",
  },
  {
    name: "Толщинный паттерн по карте ETDRS",
    value: "",
    included: true,
    section: "structure",
  },
  {
    name: "Предполагаемый паттерн заболевания",
    value: "",
    included: true,
    section: "structure",
  },
  
  // ========== ЗАКЛЮЧЕНИЕ ==========
  // Поля 32-37 (две колонки: врач слева, ИИ справа)
  {
    name: "Основные ОСТ-признаки",
    value: "",
    included: true,
    section: "conclusion",
  },
  {
    name: "Предварительная интерпретация / клиническое заключение по ОСТ",
    value: "",
    included: true,
    section: "conclusion",
  },
  {
    name: "Необходимость динамического наблюдения / контрольного ОСТ",
    value: "",
    included: true,
    section: "conclusion",
  },
  {
    name: "Необходимость сопоставления с ОКТ-ангиографией / ФАГ / клиническими данными",
    value: "",
    included: true,
    section: "conclusion",
  },
  {
    name: "Консультация специалиста (ретинолог и др.)",
    value: "",
    included: true,
    section: "conclusion",
  },
  {
    name: "Иные рекомендации",
    value: "",
    included: true,
    section: "conclusion",
  },
];

