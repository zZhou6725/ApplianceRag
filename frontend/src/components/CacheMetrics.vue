<template>
  <div class="cache-metrics" @click="expanded = !expanded">
    <div class="metrics-badge">
      <span class="badge-label">缓存</span>
      <span class="badge-value" :style="{color: rateColor}">{{ displayRate }}</span>
    </div>
    <div v-if="expanded" class="metrics-popup">
      <!-- L1 语义答案缓存 -->
      <div class="popup-section">
        <div class="section-label">L1 语义答案 (相似问题复用)</div>
        <div class="popup-row">
          <span>命中率</span>
          <span class="val" :style="{color: semColor}">{{ semRate }}%</span>
        </div>
        <div class="popup-row">
          <span>缓存数</span><span class="val">{{ semantic.answer_cache_size }}</span>
        </div>
      </div>
      <div class="popup-divider"></div>
      <!-- L3 文档缓存 -->
      <div class="popup-section">
        <div class="section-label">L3 文档缓存 (复用检索)</div>
        <div class="popup-row">
          <span>命中次数</span><span class="val green">{{ semantic.doc_cache_hits }}</span>
        </div>
        <div class="popup-row">
          <span>缓存数</span><span class="val">{{ semantic.doc_cache_size }}</span>
        </div>
      </div>
      <div class="popup-divider"></div>
      <!-- 精确缓存 -->
      <div class="popup-row"><span>L2 精确匹配</span><span class="val">{{ metrics.hits }} hits</span></div>
      <div class="popup-row"><span>总请求</span><span class="val">{{ metrics.total }}</span></div>
      <div class="popup-row"><span>命中耗时</span><span class="val green">{{ metrics.avg_hit_ms }}ms</span></div>
      <div class="popup-row"><span>未命中耗时</span><span class="val red">{{ metrics.avg_miss_ms }}ms</span></div>
      <div class="popup-row"><span>精确缓存条目</span><span class="val">{{ metrics.cache_entries }}</span></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from "vue";
import axios from "axios";

interface CacheStats {
  hits: number;
  misses: number;
  total: number;
  hit_rate: number;
  cache_entries: number;
  avg_hit_ms: number;
  avg_miss_ms: number;
  entries: number;
  semantic: {
    semantic_answer_hits: number;
    semantic_answer_misses: number;
    semantic_answer_rate: number;
    doc_cache_hits: number;
    answer_cache_size: number;
    doc_cache_size: number;
  };
}

const expanded = ref(false);
const metrics = reactive<CacheStats>({
  hits: 0, misses: 0, total: 0, hit_rate: 0,
  cache_entries: 0, avg_hit_ms: 0, avg_miss_ms: 0, entries: 0,
  semantic: { semantic_answer_hits: 0, semantic_answer_misses: 0,
    semantic_answer_rate: 0, doc_cache_hits: 0,
    answer_cache_size: 0, doc_cache_size: 0 },
});

let timer: ReturnType<typeof setInterval> | null = null;

const semantic = computed(() => metrics.semantic || {});
const semRate = computed(() => (semantic.value.semantic_answer_rate * 100).toFixed(0));
const semColor = computed(() => {
  const r = semantic.value.semantic_answer_rate;
  if (r >= 0.3) return "#16a34a";
  if (r >= 0.1) return "#ca8a04";
  return "#94a3b8";
});

// Overall hit rate: semantic + exact combined
const allHits = computed(() => semantic.value.semantic_answer_hits + (metrics.hits || 0));
const allTotal = computed(() => allHits.value + (metrics.misses || 0));
const displayRate = computed(() => {
  if (allTotal.value === 0) return "0%";
  return (allHits.value / allTotal.value * 100).toFixed(0) + "%";
});
const rateColor = computed(() => {
  if (allTotal.value === 0) return "#94a3b8";
  const r = allHits.value / allTotal.value;
  if (r >= 0.6) return "#16a34a";
  if (r >= 0.3) return "#ca8a04";
  return "#dc2626";
});

async function fetchMetrics() {
  try {
    const token = localStorage.getItem("token");
    const res = await axios.get("/health/metrics", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (res.data?.data?.cache) {
      const c = res.data.data.cache;
      // merge: metrics gets top-level keys, semantic gets the nested object
      Object.assign(metrics, {
        hits: c.hits || 0,
        misses: c.misses || 0,
        total: c.total || 0,
        hit_rate: c.hit_rate || 0,
        cache_entries: c.entries || 0,
        avg_hit_ms: c.avg_hit_ms || 0,
        avg_miss_ms: c.avg_miss_ms || 0,
        entries: c.entries || 0,
        semantic: c.semantic || {},
      });
    }
  } catch { /* silent */ }
}

onMounted(() => {
  fetchMetrics();
  timer = setInterval(fetchMetrics, 5000);
});

onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<style scoped>
.cache-metrics {
  position: relative;
  cursor: pointer;
  user-select: none;
}

.metrics-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  background: linear-gradient(135deg, #f5f3ff, #eef2ff);
  border: 1px solid #c7d2fe;
  border-radius: var(--radius-sm);
  font-size: 12px;
  transition: all var(--transition-fast);
}
.metrics-badge:hover {
  border-color: var(--color-primary);
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

.metrics-popup {
  position: absolute;
  bottom: calc(100% + 8px);
  right: 0;
  width: 230px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: 0 8px 24px rgba(0,0,0,0.1);
  padding: 12px 14px;
  z-index: 100;
  cursor: default;
}

.popup-section {
  margin-bottom: 2px;
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
.popup-row .val.green { color: #16a34a; }
.popup-row .val.red { color: #dc2626; }

.popup-divider {
  height: 1px;
  background: var(--color-border);
  margin: 6px 0;
}
</style>