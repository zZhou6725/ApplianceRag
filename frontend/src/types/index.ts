export interface Message {
  message_id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string | null;
}

export interface Conversation {
  conversation_id: string;
  title: string;
  messages: Message[];
  created_at: string | null;
  updated_at: string | null;
}

export interface ConversationListItem {
  conversation_id: string;
  title: string;
  message_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface ConversationListResponse {
  total: number;
  items: ConversationListItem[];
}

export interface ChatRequest {
  conversation_id: string | null;
  message: string;
  file_context?: string | null;
  file_name?: string | null;
}

export interface FileUploadResult {
  filename: string;
  file_size: number;
  preview: string;
  content: string;
  char_count: number;
}

export interface UploadedFile {
  name: string;
  size: number;
  content: string;
  preview: string;
}

export interface StreamTokenEvent {
  type: "token";
  content: string;
}

export interface StreamDoneEvent {
  type: "done";
  conversation_id: string;
}

export interface StreamErrorEvent {
  type: "error";
  detail: string;
}

export type StreamEvent = StreamTokenEvent | StreamDoneEvent | StreamErrorEvent;
