import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Microscope, Plus, Loader2,
  ClipboardList, ArrowLeft, ChevronRight,
} from "lucide-react";
import { useLocation } from "wouter";
import { toast } from "sonner";
import { DIRECTIONS, TEMPLATES, Direction, Category, StudyOption } from "@/constants/directions";
import { Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb";
import { useAppLayout } from "@/components/AppLayout";

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
      const result = await createStudyMutation.mutateAsync({
        title: `${studyTitle} - ${new Date().toLocaleDateString("ru-RU")}`,
        studyType: selectedType,
      });
      toast.success("Исследование создано");
      setIsCreateDialogOpen(false);
      const type = selectedType;
      const templateId = selectedTemplateId;
      resetDialogState();
      navigate(`/new-study?id=${result.id}${type ? `&type=${type}` : ""}${templateId ? `&templateId=${templateId}` : ""}`);
    } catch {
      toast.error("Ошибка при создании исследования");
    } finally {
      setIsCreating(false);
    }
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
      <div className="h-full flex items-center justify-center bg-gradient-to-br from-background via-accent/10 to-background">
        <div className="text-center max-w-md animate-fade-in-up">
          <div className="mb-6 inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/15 to-primary/5">
            <Microscope className="h-10 w-10 text-primary/60" />
          </div>
          <h3 className="text-xl font-semibold text-foreground mb-2">Выберите исследование</h3>
          <p className="text-sm text-muted-foreground mb-6 leading-relaxed">
            Выберите исследование из списка слева, чтобы просмотреть результаты,
            или создайте новое для начала анализа.
          </p>
          <Button onClick={() => setIsCreateDialogOpen(true)} className="shadow-lg">
            <Plus className="h-4 w-4 mr-2" />
            Создать исследование
          </Button>
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

          <div className="flex justify-between items-center gap-3 pt-4 border-t">
            <Button variant="outline" onClick={handleBack} disabled={!currentDirection && !currentCategory && !expandedTemplateCategory && !selectedTemplateId}>
              <ArrowLeft className="h-4 w-4 mr-2" /> Назад
            </Button>
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
