<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <a-button class="new-chat-btn" block @click="$emit('new-chat')">
        <template #icon><plus-outlined /></template>
        新建对话
      </a-button>
    </div>
    <div class="sidebar-body">
      <div class="sidebar-stats" v-if="conversations.length>0">
        <span class="stats-text">{{ conversations.length }} 个对话</span>
      </div>
      <a-spin :spinning="loading" class="sidebar-spin">
        <div v-if="conversations.length===0&&!loading" class="empty-state">
          <div class="empty-icon-wrap"><message-outlined class="empty-icon" /></div>
          <p class="empty-text">暂无对话记录</p>
          <p class="empty-hint">点击上方按钮开始</p>
        </div>
        <div v-for="conv in conversations" :key="conv.conversation_id"
          :class="['conv-card',{active:activeId===conv.conversation_id}]"
          @click="$emit('select',conv.conversation_id)">
          <div class="conv-main">
            <div class="conv-title">{{ conv.title }}</div>
            <div class="conv-footer">
              <span class="conv-count">{{ conv.message_count }} 条消息</span>
              <span class="conv-dot">·</span>
              <span class="conv-date">{{ formatDate(conv.updated_at) }}</span>
            </div>
          </div>
          <a-popconfirm title="确定删除此对话？" ok-text="删除" cancel-text="取消" placement="right"
            @confirm.stop="$emit('delete',conv.conversation_id)">
            <button class="conv-delete-btn" @click.stop><delete-outlined /></button>
          </a-popconfirm>
        </div>
      </a-spin>
    </div>
  </div>
</template>

<script setup lang="ts">
import { PlusOutlined, DeleteOutlined, MessageOutlined } from "@ant-design/icons-vue";
import type { ConversationListItem } from "../types";
defineProps<{ conversations:ConversationListItem[]; activeId:string|null; loading:boolean }>();
defineEmits<{ select:[id:string]; delete:[id:string]; 'new-chat':[] }>();
function formatDate(d:string|null):string{
  if(!d)return"未知"; const t=new Date(d); const n=new Date(); const diff=n.getTime()-t.getTime();
  if(diff<86400000)return t.toLocaleTimeString("zh-CN",{hour:"2-digit",minute:"2-digit"});
  if(diff<604800000){const days=["周日","周一","周二","周三","周四","周五","周六"];return days[t.getDay()]}
  return t.toLocaleDateString("zh-CN",{month:"short",day:"numeric"});
}
</script>

<style scoped>
.sidebar { display:flex; flex-direction:column; height:100%; }
.sidebar-header { padding:14px 12px 12px; flex-shrink:0; }
.new-chat-btn {
  height:38px; border-radius:var(--radius-sm); font-weight:600; font-size:13px;
  background: linear-gradient(135deg, #4f46e5, #6366f1); border:none; color:#fff;
  box-shadow:0 2px 10px rgba(79,70,229,0.25);
  transition:all var(--transition-fast);
}
.new-chat-btn:hover { background:linear-gradient(135deg,#4338ca,#4f46e5)!important; color:#fff!important; box-shadow:0 4px 16px rgba(79,70,229,0.35)!important; transform:translateY(-1px); }

.sidebar-body { flex:1; overflow-y:auto; padding:0 8px 10px; }
.sidebar-stats { padding:0 6px 10px; }
.stats-text { font-size:11px; font-weight:600; color:var(--color-text-muted); text-transform:uppercase; letter-spacing:0.5px; }

.empty-state { text-align:center; padding:56px 16px 0; }
.empty-icon-wrap { width:48px; height:48px; border-radius:50%; background:linear-gradient(135deg,#eef2ff,#f5f3ff); display:flex; align-items:center; justify-content:center; margin:0 auto 14px; }
.empty-icon { font-size:22px; color:var(--color-primary); opacity:0.5; }
.empty-text { font-size:13px; color:var(--color-text-secondary); margin-bottom:4px; font-weight:500; }
.empty-hint { font-size:12px; color:var(--color-text-muted); }

.conv-card {
  display:flex; align-items:center; gap:6px; padding:10px 12px;
  border-radius:var(--radius-sm); cursor:pointer;
  transition:all var(--transition-fast); margin-bottom:2px;
  border:1px solid transparent; position:relative;
}
.conv-card:hover { background:rgba(255,255,255,0.75); border-color:#dde1eb; box-shadow:var(--shadow-xs); }
.conv-card.active {
  background: linear-gradient(135deg, #f5f3ff, #eef2ff);
  border-color:#c7d2fe; box-shadow:0 0 0 1px rgba(79,70,229,0.1), var(--shadow-sm);
}
.conv-card.active .conv-title { color:var(--color-primary); font-weight:600; }

.conv-main { flex:1; min-width:0; }
.conv-title { font-size:13px; font-weight:500; color:var(--color-text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; line-height:1.4; }
.conv-footer { display:flex; align-items:center; gap:5px; margin-top:3px; font-size:11.5px; }
.conv-count,.conv-date { color:var(--color-text-muted); }
.conv-dot { color:var(--color-border); }

.conv-delete-btn { width:26px; height:26px; border:none; background:transparent; color:var(--color-text-muted); border-radius:4px; cursor:pointer; display:flex; align-items:center; justify-content:center; font-size:13px; flex-shrink:0; opacity:0; transition:all var(--transition-fast); }
.conv-card:hover .conv-delete-btn { opacity:0.5; }
.conv-delete-btn:hover { opacity:1!important; color:#ef4444; background:#fef2f2; }
</style>