import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Microscope, Plus, Loader2,
  ClipboardList, ArrowLeft, ChevronRight,
  Brain, Bone, Eye, Activity
} from "lucide-react";
import { useLocation } from "wouter";
import { toast } from "sonner";
import { DIRECTIONS, TEMPLATES, Direction, Category, StudyOption } from "@/constants/directions";
import { Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb";
import { useAppLayout } from "@/components/AppLayout";
import { motion } from "framer-motion";

const LungsIcon = ({ className }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
  >
    <path d="M12 2v5" />
    <path d="M11.5 7C7.5 5 4 6.5 4 11s2 8 4 8 3.5-3.5 3.5-3.5V7Z" />
    <path d="M12.5 7C16.5 5 20 6.5 20 11s-2 8-4 8-3.5-3.5-3.5-3.5V7Z" />
  </svg>
);

const NEW_ORGANS = [
  { id: "brain", name: "Головной мозг", desc: "МРТ / КТ", icon: Brain },
  { id: "lungs", name: "Легкие", desc: "Рентген / КТ", icon: LungsIcon },
  { id: "bone", name: "Опорно-двигательный аппарат", desc: "Рентген / КТ / МРТ", icon: Bone },
  { id: "eye", name: "Органы зрения", desc: "ОКТ Сетчатки", icon: Eye },
];

export default function Dashboard() {
  const queryClient = useQueryClient();
  const [, navigate] = useLocation();
  const { requestCreateDialog, clearCreateDialogRequest } = useAppLayout();

  // Create dialog state
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [currentDirection, setCurrentDirection] = useState<Direction | null>(null);
  const [currentCategory, setCurrentCategory] = useState<Category | null>(null);
  const [expandedTemplateCategory, setExpandedTemplateCategory] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  // Listen for create dialog requests from AppLayout sidebar
  useEffect(() => {
    if (requestCreateDialog) {
      setIsCreateDialogOpen(true);
      clearCreateDialogRequest();
    }
  }, [requestCreateDialog, clearCreateDialogRequest]);

  const createStudyMutation = useMutation({
    mutationFn: (data: { title: string; studyType: string }) => api.studies.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["studies"] });
    },
  });

  const handleCreateStudy = async () => {
    if (!selectedType) return;
    setIsCreating(true);
    try {
      let studyTitle = selectedType;
      for (const direction of DIRECTIONS) {
        for (const category of direction.categories) {
          const study = category.studies.find((s) => s.id === selectedType);
          if (study) { studyTitle = study.title; break; }
        }
        if (studyTitle !== selectedType) break;
      }
      
      setIsCreateDialogOpen(false);
      const type = selectedType;
      const templateId = selectedTemplateId;
      resetDialogState();
      
      const params = new URLSearchParams();
      if (type) params.set("type", type);
      if (templateId) params.set("templateId", templateId);
      params.set("title", studyTitle);
      
      navigate(`/new-study?${params.toString()}`);
    } finally {
      setIsCreating(false);
    }
  };

  const handleDirectCreate = (organId: string, organName: string) => {
    const params = new URLSearchParams();
    params.set("type", organId);
    params.set("title", organName);
    navigate(`/new-study?${params.toString()}`);
  };

  const resetDialogState = () => {
    setSelectedType(null);
    setSelectedTemplateId(null);
    setCurrentDirection(null);
    setCurrentCategory(null);
    setExpandedTemplateCategory(null);
  };

  const handleDirectionSelect = (direction: Direction) => {
    setCurrentDirection(direction);
    setCurrentCategory(null);
    setSelectedType(null);
    setSelectedTemplateId(null);
  };

  const handleStudySelect = (study: StudyOption, categoryId: string) => {
    if (study.id === "template_form") {
      if (expandedTemplateCategory === categoryId) {
        setExpandedTemplateCategory(null);
        setSelectedType(null);
        setSelectedTemplateId(null);
      } else {
        setExpandedTemplateCategory(categoryId);
        setSelectedType("template_form");
        setSelectedTemplateId(study.templateId || null);
      }
    } else {
      setSelectedType(study.id);
      setSelectedTemplateId(null);
      setExpandedTemplateCategory(null);
    }
  };

  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplateId(templateId);
    setSelectedType("template_form");
  };

  const handleBack = () => {
    if (selectedTemplateId) {
      setSelectedTemplateId(null);
      setSelectedType(null);
      setExpandedTemplateCategory(null);
    } else if (expandedTemplateCategory) {
      setExpandedTemplateCategory(null);
      setSelectedType(null);
    } else if (currentCategory) {
      setCurrentCategory(null);
      setSelectedType(null);
      setExpandedTemplateCategory(null);
    } else if (currentDirection) {
      setCurrentDirection(null);
      setExpandedTemplateCategory(null);
    }
  };

  return (
    <>
      {/* Empty state — welcome screen */}
      <div className="h-full flex items-start pt-12 justify-center bg-gradient-to-br from-background via-accent/10 to-background overflow-y-auto">
        <div className="max-w-5xl mx-auto w-full px-4 sm:px-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-slate-800 tracking-tight">
              Новое исследование
            </h2>
            <p className="text-slate-500 mt-1.5">
              Выберите область загрузки снимков для автоматизированного анализа.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
            {NEW_ORGANS.map((organ, idx) => {
              const Icon = organ.icon;
              return (
                <motion.button
                  key={organ.id}
                  onClick={() => {
                    if (organ.id === "eye") {
                      setIsCreateDialogOpen(true);
                      const ophthalmologyDir = DIRECTIONS.find(d => d.id === "ophthalmology");
                      if (ophthalmologyDir) handleDirectionSelect(ophthalmologyDir);
                    } else {
                      handleDirectCreate(organ.id, organ.name);
                    }
                  }}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1, duration: 0.4 }}
                  whileHover={{ scale: 1.02, y: -2 }}
                  whileTap={{ scale: 0.98 }}
                  className="group relative flex flex-col items-start p-6 rounded-2xl bg-white border border-slate-200 hover:border-blue-300 shadow-sm hover:shadow-md transition-all duration-300 text-left w-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                >
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-0 bg-blue-500 rounded-r-md group-hover:h-12 transition-all duration-300 ease-out" />
                  
                  <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center mb-4 text-slate-600 group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors duration-300">
                    <Icon className="w-6 h-6" />
                  </div>
                  
                  <h3 className="text-lg font-semibold text-slate-800 tracking-tight group-hover:text-blue-700 transition-colors mb-1 leading-tight">
                    {organ.name}
                  </h3>
                  <p className="text-sm text-slate-500 group-hover:text-slate-600 transition-colors line-clamp-2">
                    {organ.desc}
                  </p>
                </motion.button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Create Study Dialog */}
      <Dialog
        open={isCreateDialogOpen}
        onOpenChange={(open) => {
          setIsCreateDialogOpen(open);
          if (!open) resetDialogState();
        }}
      >
        <DialogContent className="sm:max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl">Выберите тип исследования</DialogTitle>
            <DialogDescription>Выберите направление и тип исследования</DialogDescription>
          </DialogHeader>

          {/* Breadcrumb */}
          {(currentDirection || currentCategory || expandedTemplateCategory) && (
            <Breadcrumb className="mb-4">
              <BreadcrumbList>
                <BreadcrumbItem>
                  <BreadcrumbLink className="cursor-pointer" onClick={() => {
                    setCurrentDirection(null); setCurrentCategory(null);
                    setSelectedType(null); setSelectedTemplateId(null); setExpandedTemplateCategory(null);
                  }}>Направления</BreadcrumbLink>
                </BreadcrumbItem>
                {currentDirection && (
                  <>
                    <BreadcrumbSeparator />
                    <BreadcrumbItem>
                      {currentCategory || selectedTemplateId ? (
                        <BreadcrumbLink className="cursor-pointer" onClick={handleBack}>{currentDirection.title}</BreadcrumbLink>
                      ) : (
                        <BreadcrumbPage>{currentDirection.title}</BreadcrumbPage>
                      )}
                    </BreadcrumbItem>
                  </>
                )}
                {currentCategory && (
                  <>
                    <BreadcrumbSeparator />
                    <BreadcrumbItem>
                      {selectedTemplateId ? (
                        <BreadcrumbLink className="cursor-pointer" onClick={handleBack}>{currentCategory.title}</BreadcrumbLink>
                      ) : (
                        <BreadcrumbPage>{currentCategory.title}</BreadcrumbPage>
                      )}
                    </BreadcrumbItem>
                  </>
                )}
              </BreadcrumbList>
            </Breadcrumb>
          )}

          <div className="py-4">
            {/* Level 1: Directions */}
            {!currentDirection && !currentCategory && !selectedTemplateId && (
              <div className="space-y-3">
                {DIRECTIONS.map((direction) => {
                  const Icon = direction.icon;
                  return (
                    <Card key={direction.id} className="cursor-pointer transition-all hover:shadow-lg" onClick={() => handleDirectionSelect(direction)}>
                      <CardHeader>
                        <div className="flex items-center gap-4">
                          <div className={`${direction.color} p-4 rounded-lg`}>
                            <Icon className="h-8 w-8 text-white" />
                          </div>
                          <div className="flex-1">
                            <CardTitle className="text-lg">{direction.title}</CardTitle>
                          </div>
                          <ChevronRight className="h-5 w-5 text-muted-foreground" />
                        </div>
                      </CardHeader>
                    </Card>
                  );
                })}
              </div>
            )}

            {/* Level 2: Categories */}
            {currentDirection && !currentCategory && (
              <div className="space-y-4">
                {currentDirection.categories.map((category) => {
                  const isTemplateExpanded = expandedTemplateCategory === category.id;
                  const availableTemplates = Object.values(TEMPLATES).filter((t) => t.direction === currentDirection.id);
                  return (
                    <div key={category.id}>
                      <h3 className="text-lg font-semibold mb-3">{category.title}</h3>
                      <div className="space-y-3">
                        {category.studies.map((study) => {
                          const Icon = study.icon;
                          const isTemplateForm = study.id === "template_form";
                          const isSelected = selectedType === study.id && !isTemplateForm;
                          const isExpanded = isTemplateForm && isTemplateExpanded;
                          return (
                            <div key={study.id} className="space-y-2">
                              <Card
                                className={`cursor-pointer transition-all ${isSelected || isExpanded ? "ring-2 ring-primary shadow-lg" : "hover:shadow-md"} ${isTemplateForm ? "bg-indigo-50/50 border-indigo-200" : ""}`}
                                onClick={() => handleStudySelect(study, category.id)}
                              >
                                <CardHeader>
                                  <div className="flex items-start gap-3">
                                    <div className={`${study.color} p-2 rounded-lg`}>
                                      <Icon className="h-5 w-5 text-white" />
                                    </div>
                                    <div className="flex-1">
                                      <CardTitle className="text-base mb-1 flex items-center gap-2">
                                        {study.title}
                                        {isTemplateForm && (
                                          <span className="text-xs font-normal text-muted-foreground bg-indigo-100 px-2 py-0.5 rounded">
                                            {availableTemplates.length} шаблон{availableTemplates.length !== 1 ? "ов" : ""}
                                          </span>
                                        )}
                                      </CardTitle>
                                      {study.description && <CardDescription className="text-xs">{study.description}</CardDescription>}
                                    </div>
                                    {isTemplateForm && (
                                      <div className={`transition-transform ${isExpanded ? "rotate-90" : ""}`}>
                                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                      </div>
                                    )}
                                  </div>
                                </CardHeader>
                              </Card>
                              {isTemplateForm && isTemplateExpanded && (
                                <div className="ml-4 space-y-2 pl-4 border-l-2 border-indigo-200">
                                  {availableTemplates.length > 0 ? (
                                    availableTemplates.map((template) => {
                                      const isTemplateSelected = selectedTemplateId === template.id;
                                      return (
                                        <Card key={template.id} className={`cursor-pointer transition-all ${isTemplateSelected ? "ring-2 ring-indigo-500 shadow-md bg-indigo-50" : "hover:shadow-sm hover:bg-indigo-50/30"}`} onClick={() => handleTemplateSelect(template.id)}>
                                          <CardHeader className="py-3">
                                            <div className="flex items-center gap-3">
                                              <div className="bg-indigo-500 p-1.5 rounded"><ClipboardList className="h-4 w-4 text-white" /></div>
                                              <div className="flex-1"><CardTitle className="text-sm font-medium">{template.title}</CardTitle></div>
                                              {isTemplateSelected && <div className="h-2 w-2 rounded-full bg-indigo-500" />}
                                            </div>
                                          </CardHeader>
                                        </Card>
                                      );
                                    })
                                  ) : (
                                    <div className="text-sm text-muted-foreground py-2">Шаблоны не найдены</div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="flex justify-end items-center gap-3 pt-4 border-t">
            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>Отмена</Button>
              <Button onClick={handleCreateStudy} disabled={!selectedType || isCreating}>
                {isCreating ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Создание...</> : <><Plus className="h-4 w-4 mr-2" /> Создать</>}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
