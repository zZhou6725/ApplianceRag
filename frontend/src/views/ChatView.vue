<template>
  <div class="chat-layout">
    <!-- Sidebar -->
    <aside class="chat-sidebar">
      <ConversationList
        :conversations="conversations"
        :active-id="activeConversationId"
        :loading="listLoading"
        @select="selectConversation"
        @delete="handleDelete"
        @new-chat="startNewChat"
      />
    </aside>

    <!-- Main Chat -->
    <section class="chat-main">
      <div class="chat-messages" ref="messagesContainer">
        <!-- Decorative blobs -->
        <div class="bg-decor">
          <div class="bg-blob blob-1"></div>
          <div class="bg-blob blob-2"></div>
          <div class="bg-blob blob-3"></div>
        </div>

        <!-- Welcome -->
        <div v-if="messages.length === 0 && !isStreaming" class="welcome">
          <div class="welcome-graphic">
            <div class="graphic-ring outer"></div>
            <div class="graphic-ring mid"></div>
            <div class="graphic-ring inner"></div>
            <robot-outlined class="graphic-icon" />
          </div>
          <h2 class="welcome-title">您好，我是 ApplianceRAG</h2>
          <p class="welcome-desc">
            智能家电客服助手，支持冰箱、空调、洗衣机、扫地机器人等产品咨询、使用指导、报告生成
          </p>
          <div class="quick-chips">
            <button v-for="(q,i) in quickQuestions" :key="i" class="quick-chip" @click="sendMessage(q)">{{ q }}</button>
          </div>
        </div>

        <!-- History messages -->
        <ChatMessage v-for="msg in messages" :key="msg.message_id" :role="msg.role" :content="msg.content" />

        <!-- Streaming -->
        <div v-if="streamingContent" class="msg-row">
          <div class="msg-avatar"><div class="avatar-bot"><robot-outlined /></div></div>
          <div class="msg-body body-bot streaming-bubble">
            <div class="bot-text markdown-content" v-html="renderedStreamingContent"></div>
            <span class="cursor-blink">|</span>
          </div>
        </div>

        <!-- Error banner -->
        <div v-if="streamError" class="error-banner">
          <span class="error-icon">&#9888;</span>
          <span class="error-text">{{ streamError }}</span>
          <button class="error-dismiss" @click="streamError=''">&times;</button>
        </div>

        <div ref="scrollAnchor"></div>
      </div>

      <div class="chat-footer">
        <div class="footer-toolbar">
          <CacheMetrics />
          <RagMetrics />
          <ExportButton :conversation-id="activeConversationId||''" :disabled="messages.length===0" />
        </div>
        <ChatInput :is-streaming="isStreaming" @send="(msg,fc,fn) => sendMessage(msg,fc,fn)" @stop="stopStreaming" />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted } from "vue";
import { marked } from "marked";
import { RobotOutlined } from "@ant-design/icons-vue";
import ConversationList from "../components/ConversationList.vue";
import ChatMessage from "../components/ChatMessage.vue";
import ChatInput from "../components/ChatInput.vue";
import ExportButton from "../components/ExportButton.vue";
import CacheMetrics from "../components/CacheMetrics.vue";
import RagMetrics from "../components/RagMetrics.vue";
import { listConversations, getConversation, deleteConversation, streamChat } from "../services/api";
import type { ConversationListItem, Message } from "../types";

const quickQuestions = [
  "冰箱不制冷怎么办？",
  "空调多久清洗一次？",
  "扫地机器人如何日常保养？",
  "查看我的使用报告",
];

const conversations = ref<ConversationListItem[]>([]);
const messages = ref<Message[]>([]);
const activeConversationId = ref<string|null>(null);
const listLoading = ref(false);
const isStreaming = ref(false);
const streamingContent = ref("");
const streamError = ref("");
let abortController: AbortController|null = null;
const scrollAnchor = ref<HTMLElement|null>(null);
const renderedStreamingContent = computed(() => { try{return marked.parse(streamingContent.value,{breaks:true})as string}catch{return streamingContent.value} });

onMounted(()=>{ loadConversationList(); });
watch(streamingContent,()=>{ nextTick(scrollToBottom); });

async function loadConversationList(){ listLoading.value=true; try{const r=await listConversations();conversations.value=r.items}catch{}finally{listLoading.value=false} }
async function selectConversation(id:string){ activeConversationId.value=id; try{const c=await getConversation(id);messages.value=c.messages;await nextTick(scrollToBottom)}catch{messages.value=[]}; await loadConversationList(); }
function startNewChat(){ messages.value=[]; activeConversationId.value=null; streamingContent.value=""; streamError.value=""; }
async function handleDelete(id:string){ await deleteConversation(id); if(activeConversationId.value===id)startNewChat(); await loadConversationList(); }
function scrollToBottom(){ scrollAnchor.value?.scrollIntoView({behavior:"smooth"}); }

async function sendMessage(text:string, fileContext?:string|null, fileName?:string|null){
  if(isStreaming.value)return;
  streamError.value="";
  messages.value.push({message_id:`local_${Date.now()}`,conversation_id:activeConversationId.value||"",role:"user",content:text,created_at:new Date().toISOString()});
  streamingContent.value=""; isStreaming.value=true; await nextTick(scrollToBottom);
  abortController=await streamChat(activeConversationId.value,text,
    (c)=>{streamingContent.value+=c},
    (newId)=>{
      if(!activeConversationId.value)activeConversationId.value=newId;
      messages.value.push({message_id:`local_${Date.now()}_asst`,conversation_id:newId,role:"assistant",content:streamingContent.value,created_at:new Date().toISOString()});
      streamingContent.value=""; isStreaming.value=false; loadConversationList();
    },
    (e)=>{console.error(e);if(streamingContent.value){messages.value.push({message_id:`local_${Date.now()}_asst`,conversation_id:activeConversationId.value||"",role:"assistant",content:streamingContent.value,created_at:new Date().toISOString()});streamingContent.value=""}isStreaming.value=false;streamError.value=e||"请求失败，请稍后重试"},
    fileContext,
    fileName,
  );
}
function stopStreaming(){ if(abortController){abortController.abort();abortController=null} if(streamingContent.value){messages.value.push({message_id:`local_${Date.now()}_asst`,conversation_id:activeConversationId.value||"",role:"assistant",content:streamingContent.value,created_at:new Date().toISOString()});streamingContent.value=""} isStreaming.value=false; }
</script>

<style scoped>
.chat-layout { display:flex; height:calc(100vh - 52px); overflow:hidden; }

/* ── Sidebar ──────────────────────────── */
.chat-sidebar {
  width:264px; flex-shrink:0; overflow:hidden;
  background: linear-gradient(180deg, #ebeef5 0%, #f1f4f8 60%, #f8fafc 100%);
  border-right: 1px solid #d8dce6;
  box-shadow: var(--shadow-sidebar);
  position: relative; z-index:10;
}

/* ── Main area ────────────────────────── */
.chat-main {
  flex:1; display:flex; flex-direction:column; min-width:0;
  background: linear-gradient(160deg, #f6f5ff 0%, #fafbff 25%, #f8fafc 55%, #f5f7fb 100%);
  position:relative;
}
.chat-messages { flex:1; overflow-y:auto; padding:12px 0; position:relative; }
.chat-footer { flex-shrink:0; background: linear-gradient(0deg, rgba(248,250,252,0.98), transparent); padding-top:4px; }
.footer-toolbar { display:flex; justify-content:flex-end; align-items:center; gap:10px; max-width:900px; margin:0 auto; padding:0 16px; }

/* ── Background blobs ─────────────────── */
.bg-decor { position:absolute; inset:0; pointer-events:none; overflow:hidden; z-index:0; }
.bg-blob { position:absolute; border-radius:50%; filter:blur(90px); }
.blob-1 { width:500px; height:500px; top:-160px; right:-120px; background: radial-gradient(circle, rgba(99,102,241,0.10), transparent); opacity:0.5; }
.blob-2 { width:360px; height:360px; bottom:-100px; left:-80px; background: radial-gradient(circle, rgba(139,92,246,0.07), transparent); opacity:0.5; }
.blob-3 { width:280px; height:280px; top:40%; right:10%; background: radial-gradient(circle, rgba(79,70,229,0.05), transparent); opacity:0.4; }

/* ── Welcome ──────────────────────────── */
.welcome { position:relative; z-index:1; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:80px 20px 48px; text-align:center; }
.welcome-graphic { position:relative; width:96px; height:96px; display:flex; align-items:center; justify-content:center; margin-bottom:28px; }
.graphic-ring { position:absolute; border-radius:50%; }
.graphic-ring.outer { width:96px; height:96px; background: conic-gradient(from 0deg, rgba(79,70,229,0.18), rgba(124,58,237,0.06), rgba(79,70,229,0.01), rgba(79,70,229,0.18)); animation:ring-spin 12s linear infinite; }
.graphic-ring.mid { width:72px; height:72px; background: linear-gradient(135deg, rgba(79,70,229,0.12), rgba(99,102,241,0.04)); }
.graphic-ring.inner { width:48px; height:48px; background: linear-gradient(135deg, #4f46e5, #7c3aed); }
.graphic-icon { position:relative; z-index:2; font-size:24px; color:#fff; }
@keyframes ring-spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }

.welcome-title { position:relative; z-index:1; font-size:24px; font-weight:700; background: linear-gradient(135deg, #1e293b, #4f46e5); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; margin-bottom:10px; letter-spacing:-0.4px; }
.welcome-desc { position:relative; z-index:1; font-size:14px; color:var(--color-text-secondary); max-width:420px; line-height:1.7; margin-bottom:32px; }
.quick-chips { position:relative; z-index:1; display:flex; flex-wrap:wrap; justify-content:center; gap:10px; max-width:520px; }
.quick-chip { padding:9px 18px; font-size:13px; font-family:var(--font-sans); color:var(--color-text-secondary); background:var(--color-surface); border:1px solid var(--color-border); border-radius:22px; cursor:pointer; transition:all var(--transition-fast); white-space:nowrap; box-shadow:var(--shadow-xs); }
.quick-chip:hover { color:var(--color-primary); border-color:#a5b4fc; background: linear-gradient(135deg, #f5f3ff, #eef2ff); transform:translateY(-2px); box-shadow:0 4px 12px rgba(79,70,229,0.15); }

/* ── Streaming row ────────────────────── */
.msg-row { display:flex; gap:12px; padding:10px 16px; max-width:900px; margin:0 auto; width:100%; align-items:flex-start; position:relative; z-index:1; }
.msg-avatar { flex-shrink:0; padding-top:2px; }
.avatar-bot { width:34px; height:34px; border-radius:var(--radius-sm); display:flex; align-items:center; justify-content:center; font-size:16px; color:#fff; background: linear-gradient(135deg, #4f46e5, #7c3aed); }
.msg-body { max-width:85%; padding:14px 20px; line-height:1.8; font-size:14px; word-break:break-word; border-radius:var(--radius-lg); }
.body-bot { background:var(--color-surface); border:1px solid var(--color-border); border-top-left-radius:var(--radius-sm); box-shadow:var(--shadow-xs); }
.streaming-bubble { display:flex; align-items:flex-start; gap:2px; }
.bot-text { color:var(--color-text); flex:1; }
.cursor-blink { display:inline-block; color:var(--color-primary); font-weight:400; font-size:16px; line-height:1.4; animation:blink 1s step-end infinite; margin-left:1px; flex-shrink:0; align-self:flex-start; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }

/* ── Error banner ──────────────────────── */
.error-banner {
  position: relative; z-index:2;
  max-width:900px; margin:12px auto 0;
  padding:12px 40px 12px 16px;
  background: linear-gradient(135deg, #fef2f2, #fee2e2);
  border: 1px solid #fecaca;
  border-radius: var(--radius-md);
  display: flex; align-items: flex-start; gap:10px;
  font-size:13px; color: #991b1b;
  box-shadow: 0 2px 8px rgba(220,38,38,0.08);
}
.error-icon { flex-shrink:0; font-size:16px; line-height:1.4; }
.error-text { flex:1; line-height:1.6; word-break:break-word; }
.error-dismiss {
  position: absolute; top:6px; right:12px;
  width:24px; height:24px; padding:0; border:none; border-radius:50%;
  background: transparent; color:#991b1b; font-size:18px; line-height:24px;
  cursor:pointer; opacity:0.6; transition: opacity var(--transition-fast);
}
.error-dismiss:hover { opacity:1; }
</style>