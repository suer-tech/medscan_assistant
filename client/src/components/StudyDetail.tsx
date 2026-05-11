import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Save, Download, Loader2, Edit2, Send, MessageSquare,
  CheckCircle2, Clock, Pencil, ShieldAlert, AlertTriangle, ShieldCheck,
  Image as ImageIcon,
} from "lucide-react";
import { toast } from "sonner";
import {
  Priority, ReviewStatus, PRIORITY_CONFIG, REVIEW_STATUS_CONFIG,
  getPriority, getReviewStatus, setReviewStatus as saveReviewStatus,
} from "@/lib/triage";

interface StudyDetailProps {
  studyId: number;
}

const REVIEW_ICONS = { clock: Clock, pencil: Pencil, check: CheckCircle2 };
const PRIORITY_ICONS = { critical: ShieldAlert, warning: AlertTriangle, normal: ShieldCheck, unknown: ShieldCheck };

export default function StudyDetail({ studyId }: StudyDetailProps) {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [title, setTitle] = useState("");
  const [analysisResult, setAnalysisResult] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [chatMessage, setChatMessage] = useState("");
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [reviewStatus, setReviewStatusState] = useState<ReviewStatus>("pending_review");
  const chatEndRef = useRef<HTMLDivElement>(null);

  const { data: study, isLoading } = useQuery({
    queryKey: ["study", studyId],
    queryFn: () => api.studies.get(studyId),
    enabled: !!studyId,
  });

  const { data: chatMessages = [], refetch: refetchChat } = useQuery({
    queryKey: ["studyMessages", studyId],
    queryFn: () => api.studies.getMessages(studyId),
    enabled: !!studyId,
  });

  useEffect(() => {
    if (study) {
      setTitle(study.title);
      setAnalysisResult(study.analysisResult || "");
      setReviewStatusState(getReviewStatus(studyId));
      setIsEditing(false);
    }
  }, [study, studyId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const handleChangeReviewStatus = (status: ReviewStatus) => {
    saveReviewStatus(studyId, status);
    setReviewStatusState(status);
    toast.success(`Статус изменён: ${REVIEW_STATUS_CONFIG[status].label}`);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await api.studies.update(studyId, { title, analysisResult });
      queryClient.invalidateQueries({ queryKey: ["study", studyId] });
      queryClient.invalidateQueries({ queryKey: ["studies"] });
      toast.success("Изменения сохранены");
      setIsEditing(false);
    } catch {
      toast.error("Ошибка при сохранении");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      const result = await api.studies.downloadPDF(studyId);
      const byteCharacters = atob(result.pdf);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const blob = new Blob([new Uint8Array(byteNumbers)], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = result.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("PDF загружен");
    } catch {
      toast.error("Ошибка при загрузке PDF");
    } finally {
      setIsDownloading(false);
    }
  };

  const handleSendMessage = async () => {
    if (!chatMessage.trim()) return;
    setIsSendingMessage(true);
    try {
      await api.studies.sendMessage(studyId, chatMessage.trim());
      setChatMessage("");
      refetchChat();
    } catch {
      toast.error("Ошибка при отправке сообщения");
    } finally {
      setIsSendingMessage(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!study) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        Исследование не найдено
      </div>
    );
  }

  const priority = getPriority(study.analysisResult);
  const pCfg = PRIORITY_CONFIG[priority];
  const PriorityIcon = PRIORITY_ICONS[priority];
  const rCfg = REVIEW_STATUS_CONFIG[reviewStatus];

  return (
    <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar animate-fade-in-up" key={studyId}>
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <div className={`rounded-full p-1.5 ${pCfg.bgLight}`}>
                <PriorityIcon className={`h-4 w-4 ${pCfg.textColor}`} />
              </div>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${pCfg.bgLight} ${pCfg.textColor}`}>
                {pCfg.label}
              </span>
              <span className="text-xs text-muted-foreground">•</span>
              <span className="text-xs text-muted-foreground">
                {new Date(study.createdAt).toLocaleDateString("ru-RU", {
                  year: "numeric", month: "long", day: "numeric",
                })}
              </span>
            </div>
            <h2 className="text-2xl font-bold text-foreground">{study.title}</h2>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            {!isEditing ? (
              <>
                <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
                  <Edit2 className="h-3.5 w-3.5 mr-1.5" /> Редактировать
                </Button>
                <Button size="sm" onClick={handleDownload} disabled={isDownloading || !study.analysisResult}>
                  {isDownloading ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <Download className="h-3.5 w-3.5 mr-1.5" />}
                  PDF
                </Button>
              </>
            ) : (
              <>
                <Button variant="outline" size="sm" onClick={() => { setIsEditing(false); setTitle(study.title); setAnalysisResult(study.analysisResult || ""); }}>
                  Отмена
                </Button>
                <Button size="sm" onClick={handleSave} disabled={isSaving}>
                  {isSaving ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <Save className="h-3.5 w-3.5 mr-1.5" />}
                  Сохранить
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Review Status Bar */}
        <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/40 border">
          <span className="text-xs font-medium text-muted-foreground mr-1">Статус просмотра:</span>
          {(["pending_review", "in_progress", "approved"] as ReviewStatus[]).map((rs) => {
            const cfg = REVIEW_STATUS_CONFIG[rs];
            const Icon = REVIEW_ICONS[cfg.icon];
            const isActive = reviewStatus === rs;
            return (
              <button
                key={rs}
                onClick={() => handleChangeReviewStatus(rs)}
                className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md transition-all ${
                  isActive ? cfg.color + " shadow-sm" : "text-muted-foreground hover:bg-muted"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {cfg.label}
              </button>
            );
          })}
        </div>

        {/* Image */}
        <Card className="shadow-sm border-border/60 overflow-hidden">
          <CardContent className="p-0">
            {study.images && study.images.length > 0 ? (
              <div className="bg-black/5">
                <img
                  src={study.images[0].url}
                  alt="Снимок"
                  className="w-full h-auto object-contain max-h-[400px] mx-auto"
                />
              </div>
            ) : (
              <div className="flex items-center justify-center h-48 bg-muted/30">
                <div className="text-center text-muted-foreground">
                  <ImageIcon className="h-10 w-10 mx-auto mb-2 opacity-40" />
                  <p className="text-sm">Изображение не загружено</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Analysis */}
        <Card className="shadow-sm border-border/60">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Результаты анализа</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {isEditing ? (
              <>
                <div className="space-y-1.5">
                  <Label className="text-xs">Название</Label>
                  <Input value={title} onChange={(e) => setTitle(e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Заключение</Label>
                  <Textarea
                    value={analysisResult}
                    onChange={(e) => setAnalysisResult(e.target.value)}
                    className="font-mono text-sm"
                    rows={10}
                  />
                </div>
              </>
            ) : (
              <ScrollArea className="max-h-[350px] w-full rounded-lg border bg-muted/20 p-4">
                {analysisResult ? (
                  <div className="prose prose-sm max-w-none whitespace-pre-wrap text-sm leading-relaxed">
                    {analysisResult}
                  </div>
                ) : (
                  <p className="text-muted-foreground italic text-sm">Результаты анализа отсутствуют</p>
                )}
              </ScrollArea>
            )}
          </CardContent>
        </Card>

        {/* Chat */}
        <Card className="shadow-sm border-border/60">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <MessageSquare className="h-5 w-5" /> Вопросы к ИИ
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col h-[400px] overflow-hidden">
            <ScrollArea className="flex-1 pr-4 mb-4 min-w-0 overflow-y-auto">
              <div className="space-y-3 min-w-0 pr-2">
                {chatMessages.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <MessageSquare className="h-10 w-10 mx-auto mb-2 opacity-30" />
                    <p className="text-sm">Задайте вопрос по результатам исследования</p>
                  </div>
                ) : (
                  chatMessages.map((msg: any) => (
                    <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} min-w-0`}>
                      <div
                        className={`max-w-[80%] min-w-0 rounded-xl px-4 py-2.5 ${
                          msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                        }`}
                        style={{ wordBreak: "break-word", overflowWrap: "break-word" }}
                      >
                        <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                        <p className="text-[10px] opacity-60 mt-1">
                          {new Date(msg.createdAt).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                        </p>
                      </div>
                    </div>
                  ))
                )}
                <div ref={chatEndRef} />
              </div>
            </ScrollArea>
            <div className="flex gap-2">
              <Textarea
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSendMessage(); }
                }}
                placeholder="Задайте вопрос..."
                className="resize-none text-sm"
                rows={2}
                disabled={isSendingMessage}
              />
              <Button
                onClick={handleSendMessage}
                disabled={!chatMessage.trim() || isSendingMessage}
                size="icon"
                className="h-auto"
              >
                {isSendingMessage ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
