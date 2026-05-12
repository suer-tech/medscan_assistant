import { useRoute } from "wouter";
import StudyDetail from "@/components/StudyDetail";

export default function StudyView() {
  const [, params] = useRoute("/study/:id");
  const studyId = params?.id ? parseInt(params.id) : null;

  if (!studyId) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        Исследование не найдено
      </div>
    );
  }

  return (
    <div className="h-full w-full overflow-hidden flex flex-col">
      <StudyDetail studyId={studyId} />
    </div>
  );
}
