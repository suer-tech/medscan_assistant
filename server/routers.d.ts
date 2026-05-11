/**
 * TypeScript type definitions for Python backend API
 * These types match the FastAPI endpoints in server/routers.py
 */

export type AppRouter = {
  system: {
    health: {
      input: { timestamp: number };
      output: { ok: boolean };
    };
    notifyOwner: {
      input: { title: string; content: string };
      output: { success: boolean };
    };
  };
  auth: {
    me: {
      input: void;
      output: any;
    };
    login: {
      input: { email: string; password: string };
      output: { success: boolean; user?: any };
    };
    logout: {
      input: void;
      output: { success: boolean };
    };
  };
  studies: {
    list: {
      input: void;
      output: Array<{
        id: number;
        userId: number;
        title: string;
        studyType: string;
        status: string;
        analysisResult: string | null;
        createdAt: string;
        updatedAt: string;
      }>;
    };
    get: {
      input: { id: number };
      output: {
        id: number;
        userId: number;
        title: string;
        studyType: string;
        status: string;
        analysisResult: string | null;
        createdAt: string;
        updatedAt: string;
        images: Array<{
          id: number;
          studyId: number;
          fileKey: string;
          url: string;
          filename: string;
          mimeType: string;
          fileSize: number;
          createdAt: string;
        }>;
      };
    };
    create: {
      input: { title: string; studyType: "retinal_scan" | "optic_nerve" | "macular_analysis" };
      output: { id: number };
    };
    uploadImage: {
      input: { studyId: number; imageData: string; filename: string; mimeType: string };
      output: { id: number; url: string };
    };
    analyze: {
      input: { studyId: number };
      output: { success: boolean; analysisResult: string };
    };
    update: {
      input: { id: number; title?: string; analysisResult?: string };
      output: { success: boolean };
    };
    delete: {
      input: { id: number };
      output: { success: boolean };
    };
    downloadPDF: {
      input: { id: number };
      output: { pdf: string; filename: string };
    };
    getChatMessages: {
      input: { studyId: number };
      output: Array<{
        id: number;
        studyId: number;
        role: "user" | "assistant";
        content: string;
        createdAt: string;
      }>;
    };
    sendChatMessage: {
      input: { studyId: number; message: string };
      output: { success: boolean; message: string };
    };
  };
};

