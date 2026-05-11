import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import { Route, Switch, Redirect, Router as WouterRouter } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import { useAuth } from "./_core/hooks/useAuth";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import NewStudy from "./pages/NewStudy";
import StudyView from "./pages/StudyView";

// Определяем базовый путь для роутера
const getBasePath = () => {
  if (typeof window !== 'undefined') {
    const path = window.location.pathname;
    if (path.startsWith('/medical')) {
      return '/medical';
    }
  }
  return '';
};

const basePath = getBasePath();

function ProtectedRoute({ component: Component, ...rest }: { component: React.ComponentType; path: string }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Redirect to="/login" />;
  }

  return <Component />;
}

function Router() {
  // Нормализуем текущий путь, убирая базовый путь
  const getLocation = () => {
    if (typeof window === 'undefined') return '/';
    let path = window.location.pathname;
    if (basePath && path.startsWith(basePath)) {
      path = path.slice(basePath.length) || '/';
    }
    return path;
  };

  return (
    <WouterRouter base={basePath}>
      <Switch>
        <Route path="/login" component={Login} />
        <Route path="/">
          <ProtectedRoute path="/" component={Dashboard} />
        </Route>
        <Route path="/new-study">
          <ProtectedRoute path="/new-study" component={NewStudy} />
        </Route>
        <Route path="/study/:id">
          <ProtectedRoute path="/study/:id" component={StudyView} />
        </Route>
        <Route path="/404" component={NotFound} />
        <Route component={NotFound} />
      </Switch>
    </WouterRouter>
  );
}

// NOTE: About Theme
// - First choose a default theme according to your design style (dark or light bg), than change color palette in index.css
//   to keep consistent foreground/background color across components
// - If you want to make theme switchable, pass `switchable` ThemeProvider and use `useTheme` hook

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider
        defaultTheme="light"
        // switchable
      >
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
