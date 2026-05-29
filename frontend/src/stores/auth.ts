import { ref, computed } from "vue";

interface User {
  username: string;
  display_name: string;
}

const token = ref(localStorage.getItem("token") || "");
const user = ref<User | null>(null);

export function useAuth() {
  const isLoggedIn = computed(() => !!token.value);

  function setAuth(t: string, u: User) {
    token.value = t;
    user.value = u;
    localStorage.setItem("token", t);
  }

  function clearAuth() {
    token.value = "";
    user.value = null;
    localStorage.removeItem("token");
  }

  async function login(username: string, password: string) {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const body = await res.json();
    if (!res.ok || body.code !== 20000) {
      throw new Error(body.message || "登录失败");
    }
    setAuth(body.data.token, { username: body.data.username, display_name: body.data.display_name });
  }

  async function fetchMe() {
    if (!token.value) return;
    try {
      const res = await fetch("/api/auth/me", {
        headers: { Authorization: `Bearer ${token.value}` },
      });
      const body = await res.json();
      if (body.code === 20000) {
        user.value = body.data;
      } else {
        clearAuth();
      }
    } catch {
      clearAuth();
    }
  }

  function logout() {
    clearAuth();
  }

  function getToken(): string {
    return token.value;
  }

  return { token, user, isLoggedIn, login, logout, fetchMe, getToken };
}