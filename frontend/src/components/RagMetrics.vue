<template>
  <div class="rag-metrics" @click="expanded = !expanded">
    <div class="metrics-badge rag-badge">
      <span class="badge-label">RAG 检索</span>
      <span v-if="result" class="badge-value" :style="{color: scoreColor}">{{ overallScore }}</span>
      <span v-else class="badge-value dim">--</span>
    </div>
    <div v-if="expanded && result" class="metrics-popup" @click.stop>
      <div class="popup-title">RAG 检索质量评测 (K={{ result.k }})</div>
      <div class="popup-section" v-if="result.precision_at_k != null">
        <div class="section-label">Chunk 级指标</div>
        <div class="popup-row"><span>Precision@K</span><span class="val">{{ (result.precision_at_k * 100).toFixed(1) }}%</span></div>
        <div class="popup-row"><span>MRR@K</span><span class="val">{{ (result.chunk_mrr * 100).toFixed(1) }}%</span></div>
        <div class="popup-row"><span>Hit Rate@K</span><span class="val">{{ (result.chunk_hit_rate * 100).toFixed(1) }}%</span></div>
      </div>
      <div class="popup-section" v-if="result.recall_at_k != null">
        <div class="section-label">文档级指标</div>
        <div class="popup-row"><span>Recall@K</span><span class="val">{{ (result.recall_at_k * 100).toFixed(1) }}%</span></div>
        <div class="popup-row"><span>Hit Rate@K</span><span class="val">{{ (result.doc_hit_rate * 100).toFixed(1) }}%</span></div>
        <div class="popup-row"><span>MRR@K</span><span class="val">{{ (result.doc_mrr * 100).toFixed(1) }}%</span></div>
      </div>
      <div class="popup-section">
        <div class="section-label">概况</div>
        <div class="popup-row"><span>测试用例</span><span class="val">{{ result.num_cases }}</span></div>
        <div class="popup-row"><span>向量库 chunks</span><span class="val">{{ result.source_diversity.total_chunks }}</span></div>
        <div class="popup-row"><span>文档源</span><span class="val">{{ result.source_diversity.unique_sources }}</span></div>
      </div>
      <button class="refresh-btn" @click="fetchEval" :disabled="loading">
        {{ loading ? '评测中...' : '刷新' }}
      </button>
    </div>
    <div v-if="expanded && !result" class="metrics-popup" @click.stop>
      <div class="popup-title">RAG 检索质量评测</div>
      <p class="empty-hint">点击下方按钮运行评测</p>
      <button class="refresh-btn" @click="fetchEval" :disabled="loading">
        {{ loading ? '评测中...' : '运行评测' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import axios from "axios";

interface EvalResult {
  k: number;
  num_cases: number;
  precision_at_k: number | null;
  chunk_mrr: number | null;
  chunk_hit_rate: number | null;
  recall_at_k: number | null;
  doc_hit_rate: number | null;
  doc_mrr: number | null;
  source_diversity: { total_chunks: number; unique_sources: number };
}

const expanded = ref(false);
const loading = ref(false);
const result = ref<EvalResult | null>(null);

const overallScore = computed(() => {
  if (!result.value) return "--";
  const scores: number[] = [];
  if (result.value.precision_at_k != null) scores.push(result.value.precision_at_k);
  if (result.value.recall_at_k != null) scores.push(result.value.recall_at_k);
  if (scores.length === 0) return "--";
  const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
  return (avg * 100).toFixed(0) + "%";
});

const scoreColor = computed(() => {
  if (!result.value) return "#94a3b8";
  const scores: number[] = [];
  if (result.value.precision_at_k != null) scores.push(result.value.precision_at_k);
  if (result.value.recall_at_k != null) scores.push(result.value.recall_at_k);
  if (scores.length === 0) return "#94a3b8";
  const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
  if (avg >= 0.8) return "#16a34a";
  if (avg >= 0.5) return "#ca8a04";
  return "#dc2626";
});

async function fetchEval() {
  loading.value = true;
  try {
    const token = localStorage.getItem("token");
    const res = await axios.get("/health/rag-eval?k=3", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (res.data?.data) result.value = res.data.data;
  } catch { /* silent */ }
  finally { loading.value = false; }
}
</script>

<style scoped>
.rag-metrics {
  position: relative;
  cursor: pointer;
  user-select: none;
}

.rag-badge {
  background: linear-gradient(135deg, #f0fdf4, #ecfdf5) !important;
  border-color: #a7f3d0 !important;
}
.rag-badge:hover {
  border-color: #22c55e !important;
}

.metrics-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border: 1px solid #c7d2fe;
  border-radius: var(--radius-sm);
  font-size: 12px;
  transition: all var(--transition-fast);
}
.metrics-badge:hover {
  box-shadow: 0 2px 8px rgba(79,70,229,0.12);
}

.badge-label {
  color: var(--color-text-secondary);
  font-weight: 500;
}
.badge-value {
  font-weight: 700;
  font-size: 14px;
}
.badge-value.dim {
  color: #94a3b8;
  font-weight: 400;
}

.metrics-popup {
  position: absolute;
  bottom: calc(100% + 8px);
  right: 0;
  width: 240px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: 0 8px 24px rgba(0,0,0,0.1);
  padding: 14px;
  z-index: 100;
  cursor: default;
}

.popup-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border);
}

.popup-section {
  margin-bottom: 8px;
}

.section-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.popup-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  padding: 2px 0;
  color: var(--color-text-secondary);
}
.popup-row .val {
  font-weight: 600;
  color: var(--color-text);
  font-variant-numeric: tabular-nums;
}

.empty-hint {
  font-size: 12px;
  color: var(--color-text-muted);
  margin: 8px 0 10px;
  text-align: center;
}

.refresh-btn {
  width: 100%;
  margin-top: 8px;
  padding: 6px 0;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-primary);
  background: #f5f3ff;
  border: 1px solid #e0e7ff;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.refresh-btn:hover:not(:disabled) {
  background: #eef2ff;
  border-color: var(--color-primary);
}
.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>