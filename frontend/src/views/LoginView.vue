<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">
          <robot-outlined />
        </div>
        <h2>ApplianceRAG</h2>
        <p>智能客服系统 · 管理后台</p>
      </div>
      <a-form :model="form" layout="vertical" @submit.prevent="handleLogin" class="login-form">
        <a-form-item label="用户名">
          <a-input v-model:value="form.username" size="large" placeholder="请输入用户名" :disabled="loading">
            <template #prefix><user-outlined /></template>
          </a-input>
        </a-form-item>
        <a-form-item label="密码">
          <a-input-password v-model:value="form.password" size="large" placeholder="请输入密码" :disabled="loading" @press-enter="handleLogin">
            <template #prefix><lock-outlined /></template>
          </a-input-password>
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" size="large" block :loading="loading" class="login-btn">
            登 录
          </a-button>
        </a-form-item>
        <div class="login-hint">
          <span>演示账号：admin / admin123</span>
        </div>
      </a-form>
      <div v-if="errorMsg" class="login-error">
        <close-circle-outlined /> {{ errorMsg }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { RobotOutlined, UserOutlined, LockOutlined, CloseCircleOutlined } from "@ant-design/icons-vue";
import { useAuth } from "../stores/auth";

const router = useRouter();
const { login } = useAuth();

const form = reactive({ username: "admin", password: "admin123" });
const loading = ref(false);
const errorMsg = ref("");

async function handleLogin() {
  if (!form.username || !form.password) return;
  loading.value = true;
  errorMsg.value = "";
  try {
    await login(form.username, form.password);
    router.replace("/");
  } catch (e: any) {
    errorMsg.value = e.message || "登录失败，请重试";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page {
  display: flex; align-items: center; justify-content: center;
  height: 100vh; min-height: 500px;
  background: linear-gradient(150deg, #f6f5ff 0%, #f0edff 25%, #f8fafc 50%, #eef1f5 100%);
  position: relative; overflow: hidden;
}
.login-page::before {
  content: "";
  position: absolute; width: 600px; height: 600px;
  border-radius: 50%; filter: blur(120px); opacity: 0.3;
  background: radial-gradient(circle, rgba(79,70,229,0.15), transparent);
  top: -200px; right: -100px; pointer-events: none;
}
.login-page::after {
  content: "";
  position: absolute; width: 400px; height: 400px;
  border-radius: 50%; filter: blur(100px); opacity: 0.2;
  background: radial-gradient(circle, rgba(99,102,241,0.12), transparent);
  bottom: -150px; left: -80px; pointer-events: none;
}

.login-card {
  position: relative; z-index: 1;
  width: 400px;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(20px);
  border-radius: var(--radius-xl);
  padding: 44px 40px 36px;
  border: 1px solid rgba(226,232,240,0.8);
  box-shadow: 0 20px 60px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04);
}

.login-header { text-align: center; margin-bottom: 32px; }
.login-logo {
  width: 56px; height: 56px; margin: 0 auto 16px;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  border-radius: var(--radius-lg); color: #fff; font-size: 26px;
  box-shadow: 0 4px 16px rgba(79,70,229,0.3);
}
.login-header h2 { font-size: 22px; font-weight: 700; color: var(--color-text); margin-bottom: 4px; letter-spacing: -0.3px; }
.login-header p { font-size: 13px; color: var(--color-text-muted); }

.login-form :deep(.ant-input-affix-wrapper) { border-radius: var(--radius-sm); }
.login-form :deep(.ant-form-item-label label) { font-weight: 500; font-size: 13px; }
.login-btn {
  height: 44px; border-radius: var(--radius-sm); font-weight: 600; font-size: 15px;
  background: linear-gradient(135deg, #4f46e5, #6366f1); border: none;
  box-shadow: 0 4px 14px rgba(79,70,229,0.25);
  margin-top: 4px;
}
.login-btn:hover { background: linear-gradient(135deg, #4338ca, #4f46e5)!important; border:none!important; }

.login-hint { text-align: center; margin-top: -8px; }
.login-hint span { font-size: 12px; color: var(--color-text-muted); }

.login-error {
  margin-top: 12px; padding: 10px 14px;
  background: #fef2f2; color: #dc2626; border-radius: var(--radius-sm);
  font-size: 13px; display: flex; align-items: center; gap: 8px;
}
</style>