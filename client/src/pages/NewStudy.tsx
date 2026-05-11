import { useState, useCallback, useEffect } from "react";
import { useLocation } from "wouter";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { ArrowLeft, Upload, Loader2, Image as ImageIcon, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import TemplateFormFields, { TemplateField } from "@/components/TemplateFormFields";
import { DEFAULT_TEMPLATE_FIELDS } from "@/constants/ostTemplateFields";

export default function NewStudy() {
  const [, navigate] = useLocation();
  const [studyId, setStudyId] = useState<number | null>(null);
  const [studyType, setStudyType] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [userQuery, setUserQuery] = useState<string>("");
  const [templateFields, setTemplateFields] = useState<TemplateField[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Get study ID and type from URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("id");
    const type = params.get("type");
    if (id) {
      setStudyId(parseInt(id));
    } else {
      toast.error("ID исследования не найдено");
      navigate("/");
    }
    if (type) {
      setStudyType(type);
    }
  }, [navigate]);

  // Fetch study data to get type if not in URL
  useEffect(() => {
    const fetchStudy = async () => {
      if (studyId && !studyType) {
        try {
          const study = await api.studies.get(studyId);
          setStudyType(study.studyType);
        } catch (error) {
          console.error("Failed to fetch study:", error);
        }
      }
    };
    fetchStudy();
  }, [studyId, studyType]);

  // Initialize template fields for template_form type
  useEffect(() => {
    if (studyType === "template_form" && templateFields.length === 0) {
      const params = new URLSearchParams(window.location.search);
      const templateId = params.get("templateId");
      
      // For now, only ost_macular template is available
      // In future, can load different templates based on templateId
      if (!templateId || templateId === "ost_macular") {
        // Initialize with default template fields from the protocol
        setTemplateFields([...DEFAULT_TEMPLATE_FIELDS]);
      }
    }
  }, [studyType, templateFields.length]);

  const handleFileSelect = (file: File) => {
    if (!file.type.startsWith("image/")) {
      toast.error("Пожалуйста, выберите изображение");
      return;
    }

    if (file.size > 16 * 1024 * 1024) {
      toast.error("Размер файла не должен превышать 16 МБ");
      return;
    }

    setSelectedFile(file);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  }, []);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleUploadAndAnalyze = async () => {
    if (!selectedFile || !studyId) return;

    setIsUploading(true);

    try {
      // Convert file to base64
      const reader = new FileReader();
      reader.readAsDataURL(selectedFile);

      reader.onload = async () => {
        const base64 = reader.result as string;

        try {
          // Upload image
          await api.studies.uploadImage(studyId, {
            imageData: base64,
            filename: selectedFile.name,
            mimeType: selectedFile.type,
          });

          toast.success("Изображение загружено");
          setIsUploading(false);
          setIsAnalyzing(true);

          // Start analysis with optional user query or template
          if (studyType === "template_form") {
            // Filter only included fields and prepare template
            const includedFields = templateFields
              .filter((f) => f.included && f.name.trim())
              .map((f) => ({
                name: f.name.trim(),
                value: f.value.trim(),
                included: true,
              }));
            
            if (includedFields.length === 0) {
              toast.error("Добавьте хотя бы одно поле с названием");
              setIsUploading(false);
              setIsAnalyzing(false);
              return;
            }

            await api.studies.analyze(studyId, undefined, includedFields);
          } else {
            await api.studies.analyze(studyId, userQuery.trim() || undefined);
          }

          toast.success("Анализ завершен!");
          setIsAnalyzing(false);

          // Navigate to study view
          navigate(`/study/${studyId}`);
        } catch (error: any) {
          setIsUploading(false);
          setIsAnalyzing(false);
          toast.error(error.message || "Ошибка при анализе изображения");
        }
      };

      reader.onerror = () => {
        setIsUploading(false);
        toast.error("Ошибка при чтении файла");
      };
    } catch (error) {
      setIsUploading(false);
      toast.error("Ошибка при загрузке изображения");
    }
  };

  const isProcessing = isUploading || isAnalyzing;

  return (
    <div className="h-full overflow-y-auto custom-scrollbar bg-gradient-to-br from-blue-50/50 via-white to-blue-50/50">
      {/* Page Title */}
      <div className="container mx-auto px-6 pt-6 pb-4">
        <h1 className="text-xl font-bold text-foreground">Загрузка снимка</h1>
        <p className="text-sm text-muted-foreground">Загрузите рентгеновский снимок для анализа</p>
      </div>

      {/* Main Content */}
      <main className="container mx-auto px-6 pb-8 max-w-4xl">
        <Card className="shadow-lg">
          <CardHeader>
            <CardTitle>Загрузка изображения</CardTitle>
            <CardDescription>
              Перетащите файл в область ниже или выберите файл с устройства
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Upload Area */}
            {!previewUrl ? (
              <div
                className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
                  isDragging
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50 hover:bg-accent/50"
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <div className="flex flex-col items-center gap-4">
                  <div className="bg-primary/10 p-6 rounded-full">
                    <Upload className="h-12 w-12 text-primary" />
                  </div>
                  <div>
                    <p className="text-lg font-medium mb-2">
                      Перетащите изображение сюда
                    </p>
                    <p className="text-sm text-muted-foreground mb-4">
                      или
                    </p>
                    <label htmlFor="file-input">
                      <Button variant="outline" asChild>
                        <span className="cursor-pointer">
                          <ImageIcon className="h-4 w-4 mr-2" />
                          Выбрать файл
                        </span>
                      </Button>
                    </label>
                    <input
                      id="file-input"
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handleFileInputChange}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Поддерживаемые форматы: JPG, PNG, DICOM. Максимальный размер: 16 МБ
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Preview */}
                <div className="relative rounded-lg overflow-hidden border bg-black/5">
                  <img
                    src={previewUrl}
                    alt="Preview"
                    className="w-full h-auto max-h-96 object-contain mx-auto"
                  />
                </div>

                {/* File Info */}
                <div className="flex items-center justify-between p-4 bg-accent/50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                    <div>
                      <p className="font-medium text-sm">{selectedFile?.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {selectedFile && (selectedFile.size / 1024 / 1024).toFixed(2)} МБ
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setSelectedFile(null);
                      setPreviewUrl(null);
                    }}
                    disabled={isProcessing}
                  >
                    Изменить
                  </Button>
                </div>

                {/* User Query Input (only for free_query) */}
                {studyType === "free_query" && (
                  <div className="space-y-2">
                    <Label htmlFor="user-query">Ваш вопрос к ИИ</Label>
                    <Textarea
                      id="user-query"
                      placeholder="Например: Что вы видите на этом снимке? Есть ли какие-либо патологии?"
                      value={userQuery}
                      onChange={(e) => setUserQuery(e.target.value)}
                      rows={4}
                      className="resize-none"
                    />
                    <p className="text-xs text-muted-foreground">
                      Опишите, что именно вы хотите узнать о загруженном изображении
                    </p>
                  </div>
                )}

                {/* Template Form Fields (only for template_form) */}
                {studyType === "template_form" && (
                  <div className="space-y-4 border-t pt-4">
                    <TemplateFormFields
                      fields={templateFields}
                      onChange={setTemplateFields}
                    />
                  </div>
                )}

                {/* Analyze Button */}
                <div className="flex justify-end gap-3">
                  <Button
                    variant="outline"
                    onClick={() => navigate("/")}
                    disabled={isProcessing}
                  >
                    Отмена
                  </Button>
                  <Button
                    size="lg"
                    onClick={handleUploadAndAnalyze}
                    disabled={
                      isProcessing ||
                      (studyType === "free_query" && !userQuery.trim()) ||
                      (studyType === "template_form" &&
                        templateFields.filter((f) => f.included && f.name.trim()).length === 0)
                    }
                    className="min-w-40"
                  >
                    {isUploading ? (
                      <>
                        <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                        Загрузка...
                      </>
                    ) : isAnalyzing ? (
                      <>
                        <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                        Анализ...
                      </>
                    ) : (
                      "Исследовать"
                    )}
                  </Button>
                </div>

                {/* Progress Info */}
                {isProcessing && (
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm text-blue-900 font-medium mb-1">
                      {isUploading && "Загрузка изображения на сервер..."}
                      {isAnalyzing && "Анализ изображения с помощью ИИ..."}
                    </p>
                    <p className="text-xs text-blue-700">
                      Это может занять несколько секунд. Пожалуйста, не закрывайте страницу.
                    </p>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
