import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Plus, Search, Trash2, Clock, Pencil, CheckCircle2,
  AlertTriangle, ShieldAlert, ShieldCheck, HelpCircle,
  Calendar, Loader2, FileText, ImageIcon,
} from "lucide-react";
import {
  Priority, PRIORITY_CONFIG, REVIEW_STATUS_CONFIG,
  getPriority, getReviewStatus, sortByPriority,
} from "@/lib/triage";

type PriorityFilter = "all" | Priority;

const STATUS_CONFIG: Record<string, { label: string; dotClass: string; pulse?: boolean }> = {
  draft: { label: "Черновик", dotClass: "bg-slate-400" },
  analyzing: { label: "Анализ...", dotClass: "bg-amber-400", pulse: true },
  completed: { label: "Завершено", dotClass: "bg-emerald-500" },
  error: { label: "Ошибка", dotClass: "bg-red-500" },
};

const PRIORITY_ICONS = {
  critical: ShieldAlert,
  warning: AlertTriangle,
  normal: ShieldCheck,
  unknown: HelpCircle,
};

const REVIEW_ICONS_MAP = {
  clock: Clock,
  pencil: Pencil,
  check: CheckCircle2,
};

// Priority left-border colors (Tailwind arbitrary)
const PRIORITY_BORDER = {
  critical: "border-l-red-500",
  warning: "border-l-amber-400",
  normal: "border-l-emerald-500",
  unknown: "border-l-slate-300",
};

interface StudySidebarProps {
  studies: any[];
  selectedStudyId: number | null;
  onSelectStudy: (id: number) => void;
  onCreateStudy: () => void;
  onDeleteStudy: (id: number) => void;
  isLoading: boolean;
}

export default function StudySidebar({
  studies,
  selectedStudyId,
  onSelectStudy,
  onCreateStudy,
  onDeleteStudy,
  isLoading,
}: StudySidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>("all");

  const filtered = (studies || []).filter((s) => {
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!s.title?.toLowerCase().includes(q)) return false;
    }
    if (priorityFilter !== "all") {
      if (getPriority(s.analysisResult) !== priorityFilter) return false;
    }
    return true;
  });

  const sorted = sortByPriority(filtered);

  const priorityCounts = {
    all: (studies || []).length,
    critical: (studies || []).filter((s) => getPriority(s.analysisResult) === "critical").length,
    warning: (studies || []).filter((s) => getPriority(s.analysisResult) === "warning").length,
    normal: (studies || []).filter((s) => getPriority(s.analysisResult) === "normal").length,
  };

  return (
    <aside className="w-[340px] min-w-[340px] h-full border-r bg-gradient-to-b from-white to-slate-50/80 flex flex-col min-h-0">
      {/* Header */}
      <div className="p-4 space-y-3 flex-shrink-0">
        <Button onClick={onCreateStudy} className="w-full h-10 shadow-md hover:shadow-lg transition-shadow font-medium" size="sm">
          <Plus className="h-4 w-4 mr-2" />
          Новое исследование
        </Button>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/60" />
          <Input
            placeholder="Поиск..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 h-9 text-sm bg-white/80 border-slate-200 focus:bg-white transition-colors"
          />
        </div>

        {/* Triage Filter Pills */}
        <div className="flex gap-1.5 bg-slate-100/80 p-1 rounded-lg">
          {(["all", "critical", "warning", "normal"] as const).map((f) => {
            const isActive = priorityFilter === f;
            const count = priorityCounts[f];
            return (
              <button
                key={f}
                onClick={() => setPriorityFilter(f)}
                className={`flex-1 flex items-center justify-center gap-1.5 text-xs py-1.5 px-2 rounded-md font-medium transition-all duration-200 ${
                  isActive
                    ? "bg-white shadow-sm text-foreground"
                    : "text-muted-foreground hover:text-foreground/70"
                }`}
              >
                {f === "all" ? (
                  <span>Все</span>
                ) : (
                  <span className={`inline-block w-2 h-2 rounded-full ${
                    f === "critical" ? "bg-red-500" : f === "warning" ? "bg-amber-400" : "bg-emerald-500"
                  }`} />
                )}
                <span className={isActive ? "font-semibold" : ""}>{count}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Divider */}
      <div className="h-px bg-gradient-to-r from-transparent via-border to-transparent" />

      {/* Study List */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-2 space-y-1.5">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <Loader2 className="h-6 w-6 animate-spin text-primary/50" />
              <p className="text-xs text-muted-foreground">Загрузка...</p>
            </div>
          ) : sorted.length === 0 ? (
            <div className="text-center py-16 px-6">
              <div className="w-12 h-12 rounded-full bg-muted/50 flex items-center justify-center mx-auto mb-3">
                <FileText className="h-5 w-5 text-muted-foreground/50" />
              </div>
              <p className="text-sm font-medium text-muted-foreground mb-1">
                {searchQuery || priorityFilter !== "all" ? "Ничего не найдено" : "Нет исследований"}
              </p>
              <p className="text-xs text-muted-foreground/70">
                {searchQuery ? "Попробуйте изменить запрос" : "Создайте первое исследование"}
              </p>
            </div>
          ) : (
            sorted.map((study) => {
              const priority = getPriority(study.analysisResult);
              const pCfg = PRIORITY_CONFIG[priority];
              const reviewStatus = getReviewStatus(study.id);
              const rCfg = REVIEW_STATUS_CONFIG[reviewStatus];
              const ReviewIcon = REVIEW_ICONS_MAP[rCfg.icon];
              const isActive = selectedStudyId === study.id;
              const PriorityIcon = PRIORITY_ICONS[priority];
              const statusCfg = STATUS_CONFIG[study.status] || STATUS_CONFIG.draft;
              const borderColor = PRIORITY_BORDER[priority];
              const hasImages = study.imageCount > 0 || study.status !== "draft";

              return (
                <div
                  key={study.id}
                  onClick={() => onSelectStudy(study.id)}
                  className={`
                    group relative rounded-lg cursor-pointer
                    border-l-[3px] transition-all duration-200 ease-out
                    ${borderColor}
                    ${isActive
                      ? "bg-white shadow-md ring-1 ring-black/[0.04]"
                      : "bg-white/50 hover:bg-white hover:shadow-sm"
                    }
                  `}
                >
                  <div className="px-3.5 py-3">
                    {/* Row 1: Priority badge + Delete */}
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-1.5">
                        <PriorityIcon className={`h-3.5 w-3.5 ${pCfg.textColor}`} />
                        <span className={`text-[10px] font-semibold uppercase tracking-wider ${pCfg.textColor}`}>
                          {pCfg.label}
                        </span>
                      </div>
                      <button
                        onClick={(e) => { e.stopPropagation(); onDeleteStudy(study.id); }}
                        className="opacity-0 group-hover:opacity-100 transition-all duration-150 p-1 -m-1 hover:bg-red-50 rounded-md text-slate-400 hover:text-red-500"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>

                    {/* Row 2: Title */}
                    <p className={`text-[13px] font-medium leading-snug mb-2 line-clamp-2 ${
                      isActive ? "text-foreground" : "text-foreground/85"
                    }`}>
                      {study.title}
                    </p>

                    {/* Row 3: Meta info */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {/* Date */}
                        <div className="flex items-center gap-1 text-muted-foreground/70">
                          <Calendar className="h-3 w-3" />
                          <span className="text-[11px]">
                            {new Date(study.createdAt).toLocaleDateString("ru-RU", {
                              day: "numeric",
                              month: "short",
                              year: study.createdAt && new Date(study.createdAt).getFullYear() !== new Date().getFullYear() ? "2-digit" : undefined,
                            })}
                          </span>
                        </div>

                        {/* Study status dot */}
                        <div className="flex items-center gap-1">
                          <span className={`inline-block w-1.5 h-1.5 rounded-full ${statusCfg.dotClass} ${statusCfg.pulse ? "animate-pulse-dot" : ""}`} />
                          <span className="text-[11px] text-muted-foreground/70">{statusCfg.label}</span>
                        </div>
                      </div>

                      {/* Review status (only for completed) */}
                      {study.status === "completed" && (
                        <div className={`flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-md ${rCfg.color}`}>
                          <ReviewIcon className="h-3 w-3" />
                          <span className="hidden xl:inline">{rCfg.label}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="flex-shrink-0 border-t bg-white/50 px-4 py-2.5 flex items-center justify-between">
        <p className="text-[11px] text-muted-foreground/60">
          {sorted.length === (studies || []).length
            ? `${(studies || []).length} исслед.`
            : `${sorted.length} из ${(studies || []).length}`
          }
        </p>
        {searchQuery && (
          <button
            onClick={() => { setSearchQuery(""); setPriorityFilter("all"); }}
            className="text-[11px] text-primary hover:text-primary/80 font-medium transition-colors"
          >
            Сбросить
          </button>
        )}
      </div>
    </aside>
  );
}
