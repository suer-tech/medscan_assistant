import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import { Microscope } from "lucide-react";
import { useState } from "react";
import { useLocation } from "wouter";
import { toast } from "sonner";

export default function Login() {
  const [, navigate] = useLocation();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email || !password) {
      toast.error("Заполните все поля");
      return;
    }
    
    setIsLoading(true);
    try {
      const data = await api.auth.login(email, password);
      console.log("[Login] Login response:", data);
      
      // Обновляем кэш с данными пользователя СРАЗУ
      // Это важно, чтобы ProtectedRoute видел аутентификацию
      if (data?.user) {
        queryClient.setQueryData(["auth", "me"], data.user);
        console.log("[Login] User data set in cache:", data.user);
      }
      
      toast.success("Вход выполнен успешно");
      
      // Переходим на главную страницу СРАЗУ
      // useAuth уже видит пользователя из кэша
      navigate("/");
    } catch (error: any) {
      console.error("[Login] Login error:", error);
      toast.error(error?.message || "Ошибка входа. Проверьте email и пароль");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-blue-50 p-4">
      <div className="w-full max-w-md">
        {/* Logo and Title */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-4">
            <div className="bg-primary/10 p-4 rounded-2xl">
              <Microscope className="h-12 w-12 text-primary" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-foreground mb-2">
            Medical AI X-Ray
          </h1>
          <p className="text-muted-foreground">
            Интеллектуальный анализ рентгеновских снимков
          </p>
        </div>

        {/* Login Card */}
        <Card className="shadow-lg border-border/50">
          <CardHeader className="space-y-1 pb-4">
            <CardTitle className="text-2xl text-center">Вход в систему</CardTitle>
            <CardDescription className="text-center">
              Войдите для доступа к платформе анализа медицинских изображений
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Почта</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="example@mail.ru"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  required
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="password">Пароль</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Введите пароль"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  required
                />
              </div>

              <Button
                type="submit"
                className="w-full h-12 text-base font-medium"
                size="lg"
                disabled={isLoading}
              >
                {isLoading ? "Вход..." : "Войти"}
              </Button>
            </form>

            <div className="text-center text-sm text-muted-foreground mt-4">
              <p>Безопасная аутентификация для медицинских специалистов</p>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-muted-foreground">
          <p>© 2025 Medical AI X-Ray Analysis</p>
          <p className="mt-1">Профессиональная система для диагностики</p>
        </div>
      </div>
    </div>
  );
}
