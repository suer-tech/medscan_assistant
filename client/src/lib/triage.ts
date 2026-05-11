/** Triage priority levels */
export type Priority = "critical" | "warning" | "normal" | "unknown";

/** Review statuses */
export type ReviewStatus = "pending_review" | "in_progress" | "approved";

export const PRIORITY_CONFIG = {
  critical: {
    label: "Критический",
    color: "bg-red-500",
    textColor: "text-red-600",
    bgLight: "bg-red-50",
    borderColor: "border-red-200",
    dotColor: "bg-red-500",
    sortOrder: 0,
  },
  warning: {
    label: "Внимание",
    color: "bg-amber-500",
    textColor: "text-amber-600",
    bgLight: "bg-amber-50",
    borderColor: "border-amber-200",
    dotColor: "bg-amber-500",
    sortOrder: 1,
  },
  normal: {
    label: "Норма",
    color: "bg-emerald-500",
    textColor: "text-emerald-600",
    bgLight: "bg-emerald-50",
    borderColor: "border-emerald-200",
    dotColor: "bg-emerald-500",
    sortOrder: 2,
  },
  unknown: {
    label: "Не определено",
    color: "bg-gray-400",
    textColor: "text-gray-500",
    bgLight: "bg-gray-50",
    borderColor: "border-gray-200",
    dotColor: "bg-gray-400",
    sortOrder: 3,
  },
} as const;

export const REVIEW_STATUS_CONFIG = {
  pending_review: {
    label: "Ожидает просмотра",
    color: "bg-blue-100 text-blue-700",
    icon: "clock",
  },
  in_progress: {
    label: "В работе",
    color: "bg-amber-100 text-amber-700",
    icon: "pencil",
  },
  approved: {
    label: "Утверждено",
    color: "bg-emerald-100 text-emerald-700",
    icon: "check",
  },
} as const;

const CRITICAL_KEYWORDS = [
  "пневмоторакс", "опухоль", "новообразование", "метастаз",
  "перелом", "критич", "срочно", "неотложн", "экстренн",
  "злокачественн", "карцином", "саркома", "лимфома",
  "инфаркт", "тромбоз", "эмболия", "кровотечен",
  "отслойка сетчатки", "острая", "разрыв",
];

const WARNING_KEYWORDS = [
  "патолог", "отклонен", "нарушен", "изменен", "подозр",
  "увеличен", "утолщен", "деформац", "воспален",
  "отек", "инфильтр", "кист", "узел", "уплотнен",
  "дистрофи", "дегенерат", "эрози", "снижен",
  "рекомендуется", "наблюдение", "контроль",
];

const NORMAL_KEYWORDS = [
  "норм", "без патолог", "без особенност", "не выявлен",
  "в пределах нормы", "соответствует норме", "здоров",
  "без изменений", "без отклонений",
];

/** Determine priority from analysis text */
export function getPriority(analysisResult: string | null | undefined): Priority {
  if (!analysisResult) return "unknown";
  const text = analysisResult.toLowerCase();

  for (const kw of CRITICAL_KEYWORDS) {
    if (text.includes(kw)) return "critical";
  }
  for (const kw of NORMAL_KEYWORDS) {
    if (text.includes(kw)) return "normal";
  }
  for (const kw of WARNING_KEYWORDS) {
    if (text.includes(kw)) return "warning";
  }
  return "normal";
}

/** localStorage key for review statuses */
const REVIEW_KEY = "medical-review-statuses";

export function getReviewStatuses(): Record<number, ReviewStatus> {
  try {
    const raw = localStorage.getItem(REVIEW_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function getReviewStatus(studyId: number): ReviewStatus {
  return getReviewStatuses()[studyId] || "pending_review";
}

export function setReviewStatus(studyId: number, status: ReviewStatus) {
  const all = getReviewStatuses();
  all[studyId] = status;
  localStorage.setItem(REVIEW_KEY, JSON.stringify(all));
}

/** Sort studies by priority then date */
export function sortByPriority<T extends { analysisResult?: string | null; createdAt: string }>(
  studies: T[]
): T[] {
  return [...studies].sort((a, b) => {
    const pa = PRIORITY_CONFIG[getPriority(a.analysisResult)].sortOrder;
    const pb = PRIORITY_CONFIG[getPriority(b.analysisResult)].sortOrder;
    if (pa !== pb) return pa - pb;
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
  });
}
