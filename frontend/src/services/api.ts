import axios from "axios";
import type { Conversation, ConversationListResponse, FileUploadResult } from "../types";

const BASE_URL = "/api";

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
});

// 请求拦截器：自动附加 JWT Token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器：401 时跳转登录页
apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("token");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

export async function listConversations(): Promise<ConversationListResponse> {
  const { data } = await apiClient.get<{
    code: number; message: string; data: ConversationListResponse;
  }>("/conversations");
  return data.data;
}

export async function getConversation(conversationId: string): Promise<Conversation> {
  const { data } = await apiClient.get<{
    code: number; message: string; data: Conversation;
  }>(`/conversations/${conversationId}`);
  return data.data;
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await apiClient.delete(`/conversations/${conversationId}`);
}

export async function streamChat(
  conversationId: string | null,
  message: string,
  onToken: (content: string) => void,
  onDone: (newConversationId: string) => void,
  onError: (error: string) => void,
  fileContext?: string | null,
  fileName?: string | null,
): Promise<AbortController> {
  const controller = new AbortController();
  const token = localStorage.getItem("token");

  try {
    const response = await fetch(`${BASE_URL}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        conversation_id: conversationId,
        message,
        file_context: fileContext || null,
        file_name: fileName || null,
      }),
      signal: controller.signal,
    });

    const reader = response.body?.getReader();
    if (!reader) { onError("无法读取响应流"); return controller; }

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      let eventType = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          eventType = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (eventType === "token" && data.content) onToken(data.content);
            else if (eventType === "done") onDone(data.conversation_id);
            else if (eventType === "error") onError(data.detail || "未知错误");
          } catch { /* skip */ }
          eventType = "";
        }
      }
    }
  } catch (err: any) {
    if (err.name !== "AbortError") onError(err.message || "网络错误");
  }
  return controller;
}

export async function uploadFile(file: File): Promise<FileUploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.post<{
    code: number; message: string; data: FileUploadResult;
  }>("/files/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data.data;
}

export function getExportUrl(conversationId: string, format: "markdown"|"pdf"): string {
  return `${BASE_URL}/export/${conversationId}/${format}`;
}