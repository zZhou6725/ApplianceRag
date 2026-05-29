<template>
  <div :class="['msg-row', isUser ? 'msg-user' : 'msg-assistant']">
    <div class="msg-avatar" v-if="!isUser">
      <div class="avatar-bot"><robot-outlined /></div>
    </div>

    <div :class="['msg-body', isUser ? 'body-user' : 'body-bot']">
      <template v-if="isUser">
        <div class="user-text">{{ content }}</div>
      </template>
      <template v-else>
        <div class="bot-text markdown-content" v-html="renderedContent"></div>
      </template>
    </div>

    <div class="msg-avatar" v-if="isUser">
      <div class="avatar-human"><user-outlined /></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { marked } from "marked";
import { UserOutlined, RobotOutlined } from "@ant-design/icons-vue";

const props = defineProps<{ role: "user"|"assistant"; content: string }>();
const isUser = computed(()=>props.role==="user");
const renderedContent = computed(()=>{
  if(props.role==="user")return props.content;
  try{return marked.parse(props.content,{breaks:true})as string}catch{return props.content}
});
</script>

<style scoped>
.msg-row { display:flex; gap:12px; padding:8px 16px; max-width:900px; margin:0 auto; width:100%; align-items:flex-start; position:relative; z-index:1; }
.msg-user { flex-direction:row-reverse; }

.msg-avatar { flex-shrink:0; padding-top:2px; }
.avatar-bot, .avatar-human { width:34px; height:34px; border-radius:var(--radius-sm); display:flex; align-items:center; justify-content:center; font-size:16px; color:#fff; box-shadow:var(--shadow-xs); }
.avatar-bot { background: linear-gradient(135deg, #4f46e5, #7c3aed); }
.avatar-human { background: linear-gradient(135deg, #6366f1, #8b5cf6); }

.msg-body { max-width:85%; padding:14px 20px; line-height:1.8; font-size:14px; word-break:break-word; }
.body-bot {
  background: linear-gradient(135deg, #ffffff, #fafbff);
  border:1px solid #e4e7ee; border-top-left-radius:var(--radius-sm);
  border-radius:var(--radius-lg); border-top-left-radius:var(--radius-sm);
  box-shadow: 0 1px 3px rgba(0,0,0,0.03), 0 0 0 1px rgba(79,70,229,0.03);
}
.body-user {
  background: linear-gradient(135deg, #4f46e5, #6366f1);
  color:#fff; border-radius:var(--radius-lg); border-top-right-radius:var(--radius-sm);
}
.user-text { white-space:pre-wrap; font-size:14px; line-height:1.7; }
.bot-text { color:var(--color-text); }
</style>