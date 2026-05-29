<template>
  <a-dropdown :disabled="disabled" trigger="click">
    <a-button class="export-btn" :disabled="disabled" size="small">
      <template #icon><download-outlined /></template>
      导出
    </a-button>
    <template #overlay>
      <div class="export-menu">
        <div class="export-item" @click="handleExport('markdown')">
          <div class="export-item-icon">
            <file-text-outlined />
          </div>
          <div class="export-item-info">
            <span class="export-item-label">Markdown</span>
            <span class="export-item-hint">纯文本，可编辑</span>
          </div>
        </div>
        <div class="export-divider"></div>
        <div class="export-item" @click="handleExport('pdf')">
          <div class="export-item-icon pdf-icon">
            <file-pdf-outlined />
          </div>
          <div class="export-item-info">
            <span class="export-item-label">PDF</span>
            <span class="export-item-hint">排版精美，适合存档</span>
          </div>
        </div>
      </div>
    </template>
  </a-dropdown>
</template>

<script setup lang="ts">
import {
  DownloadOutlined,
  FileTextOutlined,
  FilePdfOutlined,
} from "@ant-design/icons-vue";
import { getExportUrl } from "../services/api";

const props = defineProps<{
  conversationId: string;
  disabled: boolean;
}>();

function handleExport(key: string) {
  const url = getExportUrl(props.conversationId, key as "markdown" | "pdf");
  window.open(url, "_blank");
}
</script>

<style scoped>
.export-btn {
  border-radius: var(--radius-sm);
  font-weight: 500;
  font-size: 12px;
  color: var(--color-text-secondary);
  border-color: var(--color-border);
  background: var(--color-surface);
  height: 30px;
  transition: all var(--transition-fast);
}
.export-btn:hover:not(:disabled) {
  color: var(--color-primary);
  border-color: var(--color-primary);
}
.export-btn:disabled {
  color: var(--color-text-muted);
}

:deep(.export-menu) {
  min-width: 180px;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.1), 0 2px 8px rgba(0, 0, 0, 0.06);
  padding: 6px;
  border: 1px solid var(--color-border);
}
.export-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
}
.export-item:hover {
  background: var(--color-primary-bg);
}
.export-item-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  font-size: 15px;
  color: var(--color-primary);
  background: var(--color-primary-light);
}
.export-item-icon.pdf-icon {
  color: #ef4444;
  background: #fef2f2;
}
.export-item-info {
  display: flex;
  flex-direction: column;
}
.export-item-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
}
.export-item-hint {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: -1px;
}
.export-divider {
  height: 1px;
  background: var(--color-border-light);
  margin: 2px 4px;
}
</style>