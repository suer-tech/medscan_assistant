// Простой API клиент для работы с REST API
// Определяем базовый URL API в зависимости от контекста
const getApiBase = () => {
  if (typeof window !== 'undefined') {
    const path = window.location.pathname;
    // Если приложение работает на /medical, используем /medical/api
    if (path.startsWith('/medical')) {
      return '/medical/api';
    }
  }
  return '/api';
};

const API_BASE = getApiBase();

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    credentials: "include", // Важно для cookies
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  // Если ответ пустой (например, для DELETE)
  if (response.status === 204 || response.headers.get("content-length") === "0") {
    return {} as T;
  }

  return response.json();
}

export const api = {
  // Auth
  auth: {
    me: () => apiRequest<{ id: number; openId: string; name: string; email: string; role: string } | null>("/auth/me"),
    login: (email: string, password: string) =>
      apiRequest<{ success: boolean; user: { id: number; openId: string; name: string; email: string; role: string } }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    logout: () =>
      apiRequest<{ success: boolean }>("/auth/logout", {
        method: "POST",
      }),
  },

  // Studies
  studies: {
    list: () => apiRequest<any[]>("/studies"),
    get: (id: number) => apiRequest<any>(`/studies/${id}`),
    create: (data: { title: string; studyType: string }) =>
      apiRequest<{ id: number }>("/studies", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: number, data: { title?: string; analysisResult?: string }) =>
      apiRequest<{ success: boolean }>(`/studies/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: number) =>
      apiRequest<{ success: boolean }>(`/studies/${id}`, {
        method: "DELETE",
      }),
    uploadImage: (studyId: number, data: { imageData: string; filename: string; mimeType: string }) =>
      apiRequest<{ id: number; url: string }>(`/studies/${studyId}/images`, {
        method: "POST",
        body: JSON.stringify({
          imageData: data.imageData,
          filename: data.filename,
          mimeType: data.mimeType,
        }),
      }),
    analyze: (studyId: number) =>
      apiRequest<{ success: boolean; analysisResult: string }>(`/studies/${studyId}/analyze`, {
        method: "POST",
      }),
    downloadPDF: (studyId: number) =>
      apiRequest<{ pdf: string; filename: string }>(`/studies/${studyId}/pdf`),
    getMessages: (studyId: number) =>
      apiRequest<any[]>(`/studies/${studyId}/messages`),
    sendMessage: (studyId: number, message: string) =>
      apiRequest<{ success: boolean; message: string }>(`/studies/${studyId}/messages`, {
        method: "POST",
        body: JSON.stringify({ message }),
      }),
  },
};

