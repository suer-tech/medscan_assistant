import { useState, createContext, useContext, type ReactNode } from "react";
import { useAuth } from "@/_core/hooks/useAuth";
import { api } from "@/lib/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Microscope, LogOut, PanelLeftClose, PanelLeft, Loader2 } from "lucide-react";
import { useLocation } from "wouter";
import { toast } from "sonner";
import StudySidebar from "@/components/StudySidebar";

// Context so child pages can trigger "create study" dialog, access studies, etc.
interface AppLayoutContextValue {
  studies: any[];
  studiesLoading: boolean;
  openCreateDialog: () => void;
  requestCreateDialog: boolean;
  clearCreateDialogRequest: () => void;
}

const AppLayoutContext = createContext<AppLayoutContextValue>({
  studies: [],
  studiesLoading: false,
  openCreateDialog: () => {},
  requestCreateDialog: false,
  clearCreateDialogRequest: () => {},
});

export function useAppLayout() {
  return useContext(AppLayoutContext);
}

interface AppLayoutProps {
  children: ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();
  const [location, navigate] = useLocation();

  // Determine which study is "selected" based on URL
  const getSelectedStudyId = (): number | null => {
    const studyMatch = location.match(/^\/study\/(\d+)/);
    if (studyMatch) return parseInt(studyMatch[1]);
    const newStudyMatch = location.match(/[?&]id=(\d+)/);
    if (location.startsWith("/new-study") && newStudyMatch) return parseInt(newStudyMatch[1]);
    return null;
  };
  const selectedStudyId = getSelectedStudyId();

  // Sidebar state
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [studyToDelete, setStudyToDelete] = useState<number | null>(null);
  const [requestCreateDialog, setRequestCreateDialog] = useState(false);

  const { data: studies, isLoading: studiesLoading } = useQuery({
    queryKey: ["studies"],
    queryFn: () => api.studies.list(),
  });

  const deleteStudyMutation = useMutation({
    mutationFn: (id: number) => api.studies.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["studies"] });
      toast.success("Исследование удалено");
      setStudyToDelete(null);
    },
    onError: () => toast.error("Ошибка при удалении"),
  });

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const handleSelectStudy = (id: number) => {
    const study = (studies || []).find((s: any) => s.id === id);
    if (study?.status === "draft") {
      navigate(`/new-study?id=${id}`);
    } else {
      navigate(`/study/${id}`);
    }
  };

  const contextValue: AppLayoutContextValue = {
    studies: studies || [],
    studiesLoading,
    openCreateDialog: () => setRequestCreateDialog(true),
    requestCreateDialog,
    clearCreateDialogRequest: () => setRequestCreateDialog(false),
  };

  return (
    <AppLayoutContext.Provider value={contextValue}>
      <div className="h-screen flex flex-col bg-background">
        {/* Header */}
        <header className="border-b bg-white/90 backdrop-blur-md z-10 flex-shrink-0">
          <div className="px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              {/* Sidebar toggle */}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="h-8 w-8 text-muted-foreground hover:text-foreground"
                title={sidebarOpen ? "Скрыть панель" : "Показать панель"}
              >
                {sidebarOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeft className="h-4 w-4" />}
              </Button>

              <div 
                className="flex items-center gap-2 cursor-pointer group" 
                onClick={() => navigate("/")}
                title="На главную"
              >
                <div className="bg-gradient-to-br from-primary/20 to-primary/5 p-2 rounded-xl group-hover:from-primary/30 transition-colors">
                  <Microscope className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h1 className="text-base font-bold text-foreground tracking-tight leading-none group-hover:text-primary transition-colors">МедСкан</h1>
                  <p className="text-[10px] text-muted-foreground leading-none mt-0.5">Анализ медицинских изображений</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-medium">{user?.name}</p>
                <p className="text-[11px] text-muted-foreground">{user?.email}</p>
              </div>
              <Button variant="ghost" size="sm" onClick={handleLogout} className="text-muted-foreground hover:text-foreground">
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </header>

        {/* Main Layout */}
        <div className="flex flex-1 min-h-0 overflow-hidden">
          {/* Sidebar — collapsible */}
          <div
            className={`transition-all duration-300 ease-in-out flex-shrink-0 ${
              sidebarOpen ? "w-[340px]" : "w-0"
            } overflow-hidden`}
          >
            <div className="w-[340px] h-full">
              <StudySidebar
                studies={studies || []}
                selectedStudyId={selectedStudyId}
                onSelectStudy={handleSelectStudy}
                onCreateStudy={() => navigate("/")}
                onDeleteStudy={(id) => setStudyToDelete(id)}
                isLoading={studiesLoading}
              />
            </div>
          </div>

          {/* Content Area */}
          <div className="flex-1 min-w-0 min-h-0 overflow-hidden">
            {children}
          </div>
        </div>

        {/* Delete Confirmation */}
        <AlertDialog open={studyToDelete !== null} onOpenChange={(open) => !open && setStudyToDelete(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Удалить исследование?</AlertDialogTitle>
              <AlertDialogDescription>
                Это действие нельзя отменить. Исследование будет удалено навсегда.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Отмена</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => studyToDelete && deleteStudyMutation.mutate(studyToDelete)}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                disabled={deleteStudyMutation.isPending}
              >
                {deleteStudyMutation.isPending ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Удаление...</> : "Удалить"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </AppLayoutContext.Provider>
  );
}
