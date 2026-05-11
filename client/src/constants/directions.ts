import { Eye, Activity, FlaskConical, Brain, Scan, ClipboardList, MessageSquare } from "lucide-react";
import { LucideIcon } from "lucide-react";

export interface StudyOption {
  id: string;
  title: string;
  description?: string;
  icon: LucideIcon;
  color: string;
  templateId?: string; // Для шаблонов
}

export interface Category {
  id: string;
  title: string;
  studies: StudyOption[];
}

export interface Direction {
  id: string;
  title: string;
  icon: LucideIcon;
  color: string;
  categories: Category[];
}

export const DIRECTIONS: Direction[] = [
  {
    id: "ophthalmology",
    title: "Офтальмология",
    icon: Eye,
    color: "bg-blue-500",
    categories: [
      {
        id: "ophthalmology_studies",
        title: "Типы исследований",
        studies: [
          {
            id: "retinal_scan",
            title: "Сканирование сетчатки",
            description: "Анализ состояния сетчатки глаза, выявление патологий сосудов и макулярной области",
            icon: Eye,
            color: "bg-blue-500",
          },
          {
            id: "optic_nerve",
            title: "Анализ зрительного нерва",
            description: "Оценка диска зрительного нерва, выявление признаков глаукомы и атрофии",
            icon: Brain,
            color: "bg-purple-500",
          },
          {
            id: "macular_analysis",
            title: "Анализ макулярной области",
            description: "Детальное исследование макулы, выявление дегенеративных изменений",
            icon: Scan,
            color: "bg-green-500",
          },
          {
            id: "template_form",
            title: "Запрос по шаблону",
            description: "Заполнение формы по готовому шаблону протокола",
            icon: ClipboardList,
            color: "bg-indigo-500",
            // templateId не указан, чтобы показывалось меню выбора шаблонов
          },
        ],
      },
    ],
  },
  {
    id: "ultrasound",
    title: "УЗИ",
    icon: Activity,
    color: "bg-cyan-500",
    categories: [
      {
        id: "ultrasound_studies",
        title: "Типы исследований",
        studies: [
          {
            id: "ultrasound_thyroid",
            title: "Щитовидной железы",
            description: "Ультразвуковое исследование щитовидной железы",
            icon: Activity,
            color: "bg-cyan-500",
          },
          {
            id: "ultrasound_liver",
            title: "Печени",
            description: "Ультразвуковое исследование печени",
            icon: Activity,
            color: "bg-cyan-600",
          },
          {
            id: "template_form",
            title: "Запрос по шаблону",
            description: "Заполнение формы по готовому шаблону протокола",
            icon: ClipboardList,
            color: "bg-indigo-500",
          },
        ],
      },
    ],
  },
  {
    id: "laboratory",
    title: "Лабораторная диагностика",
    icon: FlaskConical,
    color: "bg-pink-500",
    categories: [
      {
        id: "lab_studies",
        title: "Типы исследований",
        studies: [
          {
            id: "lab_blood",
            title: "Анализы крови",
            description: "Анализ результатов лабораторных исследований крови",
            icon: FlaskConical,
            color: "bg-pink-500",
          },
          {
            id: "template_form",
            title: "Запрос по шаблону",
            description: "Заполнение формы по готовому шаблону протокола",
            icon: ClipboardList,
            color: "bg-indigo-500",
          },
        ],
      },
    ],
  },
  {
    id: "other",
    title: "Другое",
    icon: MessageSquare,
    color: "bg-orange-500",
    categories: [
      {
        id: "other_studies",
        title: "Типы исследований",
        studies: [
          {
            id: "free_query",
            title: "Свободный запрос",
            description: "Задайте любой вопрос к ИИ по загруженному изображению",
            icon: MessageSquare,
            color: "bg-orange-500",
          },
        ],
      },
    ],
  },
];

// Шаблоны для разных направлений
export const TEMPLATES = {
  ost_macular: {
    id: "ost_macular",
    title: "ОСТ-снимок (макулярная область / задний полюс)",
    direction: "ophthalmology",
  },
  // Можно добавить другие шаблоны позже
};

