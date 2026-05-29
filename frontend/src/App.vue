<template>
  <div class="app-shell">
    <header class="app-header" v-if="isLoggedIn">
      <div class="header-brand">
        <div class="brand-icon"><robot-outlined /></div>
        <div class="brand-info">
          <span class="brand-text">ApplianceRAG</span>
          <span class="brand-subtitle">智能客服系统</span>
        </div>
      </div>
      <div class="header-right">
        <span class="header-status">
          <span class="status-dot"></span>
          <span class="status-text">AI 在线</span>
        </span>
        <a-dropdown trigger="click">
          <span class="user-badge">
            <a-avatar size="small" class="user-avatar">
              <template #icon><user-outlined /></template>
            </a-avatar>
            <span class="user-name">{{ user?.display_name || '用户' }}</span>
            <down-outlined class="user-arrow" />
          </span>
          <template #overlay>
            <div class="user-menu">
              <div class="user-menu-header">
                <div class="user-menu-avatar">
                  <a-avatar size="36">
                    <template #icon><user-outlined /></template>
                  </a-avatar>
                </div>
                <div>
                  <div class="user-menu-name">{{ user?.display_name }}</div>
                  <div class="user-menu-role">管理员</div>
                </div>
              </div>
              <div class="menu-divider"></div>
              <div class="menu-item logout-item" @click="handleLogout">
                <logout-outlined />
                <span>退出登录</span>
              </div>
            </div>
          </template>
        </a-dropdown>
      </div>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useRouter } from "vue-router";
import { RobotOutlined, UserOutlined, DownOutlined, LogoutOutlined } from "@ant-design/icons-vue";
import { useAuth } from "./stores/auth";

const router = useRouter();
const { user, isLoggedIn, fetchMe, logout } = useAuth();

onMounted(async () => {
  if (isLoggedIn.value) {
    await fetchMe();
  }
});

function handleLogout() {
  logout();
  router.push("/login");
}
</script>

<style scoped>
.app-shell { display:flex; flex-direction:column; height:100vh; overflow:hidden; }

.app-header {
  display:flex; align-items:center; justify-content:space-between;
  height:52px; padding:0 20px; flex-shrink:0; z-index:50;
  background: linear-gradient(135deg, #ffffff 0%, #f8f7ff 40%, #f0edff 100%);
  border-bottom: 1px solid #e4e0f4;
  box-shadow: 0 1px 4px rgba(79,70,229,0.04);
}

.header-brand { display:flex; align-items:center; gap:10px; }
.brand-icon {
  width:32px; height:32px;
  display:flex; align-items:center; justify-content:center;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  border-radius: var(--radius-sm); color:#fff; font-size:17px;
  box-shadow: 0 2px 10px rgba(79,70,229,0.3);
}
.brand-info { display:flex; align-items:baseline; gap:8px; }
.brand-text { font-size:16px; font-weight:700; color:var(--color-text); letter-spacing:-0.3px; }
.brand-subtitle { font-size:11.5px; color:var(--color-text-muted); font-weight:400; }

.header-right { display:flex; align-items:center; gap:14px; }
.header-status {
  display:flex; align-items:center; gap:7px;
  padding:5px 14px; border-radius:20px;
  background: linear-gradient(135deg, #f0fdf4, #ecfdf5);
  border:1px solid #bbf7d0;
}
.status-dot {
  width:7px; height:7px; border-radius:50%;
  background:#22c55e; box-shadow:0 0 8px rgba(34,197,94,0.4);
  animation:pulse-dot 2s ease-in-out infinite;
}
@keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:0.5} }
.status-text { font-size:12px; font-weight:600; color:#15803d; }

/* User */
.user-badge {
  display:flex; align-items:center; gap:7px; cursor:pointer;
  padding:4px 10px 4px 4px; border-radius:20px;
  transition: background var(--transition-fast);
}
.user-badge:hover { background: rgba(79,70,229,0.06); }
.user-avatar { background: linear-gradient(135deg, #6366f1, #8b5cf6); }
.user-name { font-size:13px; font-weight:500; color:var(--color-text); }
.user-arrow { font-size:10px; color:var(--color-text-muted); }

.user-menu { min-width:200px; background:#fff; border-radius:var(--radius-md); box-shadow:var(--shadow-lg); border:1px solid var(--color-border); padding:8px 6px; }
.user-menu-header { display:flex; align-items:center; gap:10px; padding:8px 8px 10px; }
.user-menu-avatar :deep(.ant-avatar) { background: linear-gradient(135deg, #6366f1, #8b5cf6); }
.user-menu-name { font-size:14px; font-weight:600; color:var(--color-text); }
.user-menu-role { font-size:12px; color:var(--color-text-muted); }
.menu-divider { height:1px; background:var(--color-border-light); margin:4px 0; }
.menu-item {
  display:flex; align-items:center; gap:10px;
  padding:9px 10px; border-radius:var(--radius-sm);
  cursor:pointer; font-size:13px; color:var(--color-text-secondary);
  transition: all var(--transition-fast);
}
.menu-item:hover { background:#fef2f2; color:#ef4444; }
.logout-item { color:#ef4444; }
</style>