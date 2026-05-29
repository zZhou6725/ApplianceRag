<template>
  <div class="input-area">
    <!-- Uploaded file chip -->
    <div v-if="uploadedFile" class="file-chip-row">
      <div class="file-chip">
        <file-text-outlined class="file-chip-icon" />
        <span class="file-chip-name">{{ uploadedFile.name }}</span>
        <span class="file-chip-size">{{ formatSize(uploadedFile.size) }}</span>
        <close-outlined class="file-chip-remove" @click="removeFile" />
      </div>
    </div>

    <div class="input-row">
      <!-- Upload button -->
      <input
        ref="fileInputRef"
        type="file"
        accept=".txt,.md,.pdf,.docx,.png,.jpg,.jpeg"
        style="display:none"
        @change="handleFileChange"
      />
      <a-tooltip title="上传文件">
        <a-button
          type="text"
          class="upload-btn"
          :disabled="isStreaming"
          @click="openFilePicker"
        >
          <template #icon><paper-clip-outlined /></template>
        </a-button>
      </a-tooltip>

      <a-textarea
        v-model:value="inputText"
        :auto-size="{ minRows: 1, maxRows: 4 }"
        placeholder="输入您的问题，Enter 发送..."
        :disabled="isStreaming"
        class="chat-textarea"
        @keydown.enter.prevent="handleSend"
      />
      <div class="input-suffix">
        <a-button
          v-if="!isStreaming"
          type="primary"
          class="send-btn"
          :disabled="!inputText.trim()"
          @click="handleSend"
        >
          <template #icon><send-outlined /></template>
        </a-button>
        <a-button
          v-else
          size="small"
          class="stop-btn"
          @click="$emit('stop')"
        >
          <template #icon><pause-circle-outlined /></template>
          停止
        </a-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import {
  SendOutlined,
  PauseCircleOutlined,
  PaperClipOutlined,
  FileTextOutlined,
  CloseOutlined,
} from "@ant-design/icons-vue";
import { uploadFile } from "../services/api";
import type { UploadedFile } from "../types";

defineProps<{
  isStreaming: boolean;
}>();

const emit = defineEmits<{
  send: [message: string, fileContext: string | null, fileName: string | null];
  stop: [];
}>();

const inputText = ref("");
const fileInputRef = ref<HTMLInputElement | null>(null);
const uploadedFile = ref<UploadedFile | null>(null);

function openFilePicker() {
  fileInputRef.value?.click();
}

async function handleFileChange(e: Event) {
  const target = e.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  try {
    const result = await uploadFile(file);
    uploadedFile.value = {
      name: result.filename,
      size: result.file_size,
      content: result.content,
      preview: result.preview,
    };
  } catch (err: any) {
    console.error("文件上传失败:", err);
  } finally {
    // reset so same file can be re-selected
    if (fileInputRef.value) fileInputRef.value.value = "";
  }
}

function removeFile() {
  uploadedFile.value = null;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

function handleSend() {
  const text = inputText.value.trim();
  if (!text) return;
  const fc = uploadedFile.value?.content ?? null;
  const fn = uploadedFile.value?.name ?? null;
  emit("send", text, fc, fn);
  inputText.value = "";
  uploadedFile.value = null;
}
</script>

<style scoped>
.input-area {
  max-width: 880px;
  margin: 0 auto;
  padding: 12px 16px 16px;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: var(--color-surface);
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 6px 8px 6px 14px;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}
.input-row:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.07);
}

.chat-textarea {
  flex: 1;
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
  font-size: 14px;
  resize: none;
}
.chat-textarea :deep(textarea) {
  border: none !important;
  box-shadow: none !important;
  padding: 6px 0 !important;
  background: transparent !important;
  font-size: 14px;
  line-height: 1.6;
  min-height: 24px;
}
.chat-textarea :deep(textarea::placeholder) {
  color: var(--color-text-muted);
}
.chat-textarea :deep(textarea:focus) {
  border: none !important;
  box-shadow: none !important;
}

.input-suffix {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding-bottom: 2px;
}

.send-btn {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
  box-shadow: none;
}
.send-btn:not(:disabled) {
  background: linear-gradient(135deg, #4f46e5, #6366f1);
  border-color: transparent;
}
.send-btn:not(:disabled):hover {
  background: linear-gradient(135deg, #4338ca, #4f46e5) !important;
  border-color: transparent !important;
}
.send-btn:disabled {
  background: #e2e8f0;
  border-color: #e2e8f0;
  color: var(--color-text-muted);
}

.stop-btn {
  border-radius: var(--radius-sm);
  font-weight: 500;
  font-size: 12px;
  color: #ef4444;
  border-color: #fecaca;
  background: #fef2f2;
  height: 30px;
}
.stop-btn:hover {
  color: #dc2626 !important;
  border-color: #fca5a5 !important;
}

/* ── File chip ─────────────────────────── */
.file-chip-row {
  max-width: 880px;
  margin: 0 auto;
  padding: 0 16px 8px;
}

.file-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px 6px 10px;
  background: linear-gradient(135deg, #f5f3ff, #eef2ff);
  border: 1px solid #c7d2fe;
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--color-text);
}

.file-chip-icon {
  color: var(--color-primary);
  font-size: 14px;
}

.file-chip-name {
  font-weight: 500;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-chip-size {
  color: var(--color-text-muted);
}

.file-chip-remove {
  cursor: pointer;
  color: var(--color-text-muted);
  font-size: 10px;
  padding: 2px;
  border-radius: 2px;
  transition: color var(--transition-fast);
}
.file-chip-remove:hover {
  color: #ef4444;
}

/* ── Upload button ─────────────────────── */
.upload-btn {
  flex-shrink: 0;
  color: var(--color-text-secondary);
  font-size: 18px;
  padding: 4px 6px;
  height: auto;
  border: none;
  align-self: flex-end;
  margin-bottom: 2px;
}
.upload-btn:hover {
  color: var(--color-primary) !important;
  background: rgba(79, 70, 229, 0.06) !important;
}
</style>