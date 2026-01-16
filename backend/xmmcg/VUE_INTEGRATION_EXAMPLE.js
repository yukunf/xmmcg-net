/**
 * Django 用户管理 API - Vue 3 Composition API 集成示例
 * 
 * 这是一个完整的 Vue 3 Composition API 示例，展示如何使用 Django 用户管理 API
 * 
 * 使用方法：
 * 1. 将此文件中的代码复制到你的 Vue 项目中
 * 2. 根据项目结构进行调整
 * 3. 确保 Django 服务器正在运行
 * 4. 更新 API 基础 URL（如果需要）
 */

// ============================================================================
// 1. API 服务 (src/services/authService.js)
// ============================================================================

import axios from 'axios';

const API_BASE_URL = process.env.VUE_APP_API_URL || 'http://localhost:8000/api/users';

const api = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true, // 重要：允许跨域请求带上 Cookie
    headers: {
        'Content-Type': 'application/json',
    },
});

// 响应拦截器 - 处理错误
api.interceptors.response.use(
    response => response,
    error => {
        if (error.response?.status === 401) {
            // 未认证，可能会话过期
            // 触发登出事件
            window.dispatchEvent(new Event('session-expired'));
        }
        return Promise.reject(error);
    }
);

export const authService = {
    // 用户注册
    register: (data) => api.post('/register/', data),
    
    // 用户登录
    login: (data) => api.post('/login/', data),
    
    // 用户登出
    logout: () => api.post('/logout/'),
    
    // 获取当前用户信息
    getCurrentUser: () => api.get('/me/'),
    
    // 更新用户个人信息
    updateProfile: (data) => api.put('/profile/', data),
    
    // 修改密码
    changePassword: (data) => api.post('/change-password/', data),
    
    // 检查用户名可用性
    checkUsername: (username) => api.post('/check-username/', { username }),
    
    // 检查邮箱可用性
    checkEmail: (email) => api.post('/check-email/', { email }),
};

export default api;


// ============================================================================
// 2. Pinia Store (src/stores/authStore.js)
// ============================================================================

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { authService } from '@/services/authService';

export const useAuthStore = defineStore('auth', () => {
    // 状态
    const user = ref(null);
    const isAuthenticated = ref(false);
    const loading = ref(false);
    const error = ref(null);

    // 计算属性
    const isLoggedIn = computed(() => !!user.value);

    // 注册
    const register = async (registerData) => {
        loading.value = true;
        error.value = null;
        try {
            const response = await authService.register(registerData);
            user.value = response.data.user;
            isAuthenticated.value = true;
            return response.data;
        } catch (err) {
            error.value = err.response?.data?.errors || { message: '注册失败' };
            throw err;
        } finally {
            loading.value = false;
        }
    };

    // 登录
    const login = async (loginData) => {
        loading.value = true;
        error.value = null;
        try {
            const response = await authService.login(loginData);
            user.value = response.data.user;
            isAuthenticated.value = true;
            return response.data;
        } catch (err) {
            error.value = err.response?.data || { message: '登录失败' };
            throw err;
        } finally {
            loading.value = false;
        }
    };

    // 登出
    const logout = async () => {
        loading.value = true;
        error.value = null;
        try {
            await authService.logout();
            user.value = null;
            isAuthenticated.value = false;
        } catch (err) {
            error.value = err.response?.data || { message: '登出失败' };
            throw err;
        } finally {
            loading.value = false;
        }
    };

    // 获取当前用户
    const fetchCurrentUser = async () => {
        loading.value = true;
        error.value = null;
        try {
            const response = await authService.getCurrentUser();
            user.value = response.data.user;
            isAuthenticated.value = true;
            return response.data.user;
        } catch (err) {
            user.value = null;
            isAuthenticated.value = false;
            error.value = err.response?.data || { message: '获取用户信息失败' };
            throw err;
        } finally {
            loading.value = false;
        }
    };

    // 更新个人信息
    const updateProfile = async (profileData) => {
        loading.value = true;
        error.value = null;
        try {
            const response = await authService.updateProfile(profileData);
            user.value = response.data.user;
            return response.data;
        } catch (err) {
            error.value = err.response?.data?.errors || { message: '更新失败' };
            throw err;
        } finally {
            loading.value = false;
        }
    };

    // 修改密码
    const changePassword = async (passwordData) => {
        loading.value = true;
        error.value = null;
        try {
            const response = await authService.changePassword(passwordData);
            return response.data;
        } catch (err) {
            error.value = err.response?.data || { message: '修改密码失败' };
            throw err;
        } finally {
            loading.value = false;
        }
    };

    // 检查用户名可用性
    const checkUsername = async (username) => {
        try {
            const response = await authService.checkUsername(username);
            return response.data.available;
        } catch (err) {
            return false;
        }
    };

    // 检查邮箱可用性
    const checkEmail = async (email) => {
        try {
            const response = await authService.checkEmail(email);
            return response.data.available;
        } catch (err) {
            return false;
        }
    };

    // 清除错误
    const clearError = () => {
        error.value = null;
    };

    return {
        // 状态
        user,
        isAuthenticated,
        loading,
        error,
        isLoggedIn,
        // 方法
        register,
        login,
        logout,
        fetchCurrentUser,
        updateProfile,
        changePassword,
        checkUsername,
        checkEmail,
        clearError,
    };
});


// ============================================================================
// 3. 路由守卫 (src/router/guards.js)
// ============================================================================

import { useAuthStore } from '@/stores/authStore';

export function setupAuthGuards(router) {
    router.beforeEach(async (to, from, next) => {
        const authStore = useAuthStore();

        // 如果路由需要认证
        if (to.meta.requiresAuth) {
            // 如果未认证，尝试获取当前用户
            if (!authStore.isLoggedIn) {
                try {
                    await authStore.fetchCurrentUser();
                    next();
                } catch (err) {
                    // 认证失败，重定向到登录
                    next('/login');
                }
            } else {
                next();
            }
        } else {
            next();
        }
    });

    // 监听会话过期事件
    window.addEventListener('session-expired', () => {
        const authStore = useAuthStore();
        authStore.logout();
        // 可以显示提示信息
    });
}

// 在路由配置中使用
// router.meta.requiresAuth = true


// ============================================================================
// 4. 注册表单组件 (src/components/RegisterForm.vue)
// ============================================================================

/*
<template>
  <div class="register-form">
    <h2>用户注册</h2>

    <!-- 错误信息 -->
    <div v-if="authStore.error" class="alert alert-error">
      <p v-for="(errors, field) in authStore.error" :key="field">
        {{ field }}: {{ Array.isArray(errors) ? errors.join(', ') : errors }}
      </p>
    </div>

    <!-- 表单 -->
    <form @submit.prevent="handleRegister">
      <!-- 用户名 -->
      <div class="form-group">
        <label for="username">用户名</label>
        <input
          v-model="form.username"
          type="text"
          id="username"
          placeholder="输入用户名"
          required
        />
        <div v-if="usernameStatus" class="status" :class="usernameStatus.class">
          {{ usernameStatus.message }}
        </div>
      </div>

      <!-- 邮箱 -->
      <div class="form-group">
        <label for="email">邮箱</label>
        <input
          v-model="form.email"
          type="email"
          id="email"
          placeholder="输入邮箱"
          required
        />
        <div v-if="emailStatus" class="status" :class="emailStatus.class">
          {{ emailStatus.message }}
        </div>
      </div>

      <!-- 密码 -->
      <div class="form-group">
        <label for="password">密码</label>
        <input
          v-model="form.password"
          type="password"
          id="password"
          placeholder="输入密码（至少8个字符）"
          required
        />
      </div>

      <!-- 确认密码 -->
      <div class="form-group">
        <label for="password_confirm">确认密码</label>
        <input
          v-model="form.password_confirm"
          type="password"
          id="password_confirm"
          placeholder="再次输入密码"
          required
        />
      </div>

      <!-- 提交按钮 -->
      <button
        type="submit"
        :disabled="authStore.loading || !isFormValid"
        class="btn btn-primary"
      >
        {{ authStore.loading ? '注册中...' : '注册' }}
      </button>
    </form>

    <!-- 登录链接 -->
    <p class="text-center mt-3">
      已有账户？<router-link to="/login">点击登录</router-link>
    </p>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/authStore';

const router = useRouter();
const authStore = useAuthStore();

// 表单数据
const form = ref({
  username: '',
  email: '',
  password: '',
  password_confirm: '',
  first_name: '',
  last_name: '',
});

// 检查状态
const usernameStatus = ref(null);
const emailStatus = ref(null);

// 检查用户名
const checkUsername = async () => {
  if (!form.value.username || form.value.username.length < 3) {
    usernameStatus.value = null;
    return;
  }

  const available = await authStore.checkUsername(form.value.username);
  usernameStatus.value = {
    message: available ? '✓ 用户名可用' : '✗ 用户名已被占用',
    class: available ? 'text-success' : 'text-danger',
  };
};

// 检查邮箱
const checkEmail = async () => {
  if (!form.value.email) {
    emailStatus.value = null;
    return;
  }

  const available = await authStore.checkEmail(form.value.email);
  emailStatus.value = {
    message: available ? '✓ 邮箱可用' : '✗ 邮箱已被使用',
    class: available ? 'text-success' : 'text-danger',
  };
};

// 防抖检查用户名
watch(
  () => form.value.username,
  () => {
    clearTimeout(usernameTimeout);
    usernameTimeout = setTimeout(checkUsername, 500);
  }
);

// 防抖检查邮箱
let emailTimeout;
watch(
  () => form.value.email,
  () => {
    clearTimeout(emailTimeout);
    emailTimeout = setTimeout(checkEmail, 500);
  }
);

// 表单验证
const isFormValid = computed(() => {
  return (
    form.value.username &&
    form.value.email &&
    form.value.password &&
    form.value.password === form.value.password_confirm &&
    form.value.password.length >= 8 &&
    usernameStatus.value?.class === 'text-success' &&
    emailStatus.value?.class === 'text-success'
  );
});

// 提交表单
const handleRegister = async () => {
  try {
    await authStore.register(form.value);
    router.push('/');
  } catch (err) {
    // 错误已在 store 中处理
  }
};

let usernameTimeout;
</script>

<style scoped>
.register-form {
  max-width: 400px;
  margin: 0 auto;
  padding: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.status {
  font-size: 12px;
  margin-top: 5px;
}

.text-success {
  color: #28a745;
}

.text-danger {
  color: #dc3545;
}

.alert {
  padding: 10px;
  margin-bottom: 20px;
  border-radius: 4px;
}

.alert-error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.btn {
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-primary:hover {
  background-color: #0056b3;
}

.btn-primary:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.text-center {
  text-align: center;
}

.mt-3 {
  margin-top: 20px;
}
</style>
*/


// ============================================================================
// 5. 环境配置 (.env.local 或 .env)
// ============================================================================

/*
# Django API 配置
VUE_APP_API_URL=http://localhost:8000/api/users

# 或者生产环境
# VUE_APP_API_URL=https://api.example.com/api/users
*/


// ============================================================================
// 6. main.js 配置示例
// ============================================================================

/*
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { setupAuthGuards } from './router/guards'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// 设置认证守卫
setupAuthGuards(router)

app.mount('#app')
*/


// ============================================================================
// 7. 路由配置示例 (src/router/index.js)
// ============================================================================

/*
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/pages/HomePage.vue'),
  },
  {
    path: '/login',
    component: () => import('@/pages/LoginPage.vue'),
  },
  {
    path: '/register',
    component: () => import('@/pages/RegisterPage.vue'),
  },
  {
    path: '/profile',
    component: () => import('@/pages/ProfilePage.vue'),
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
*/


// ============================================================================
// 8. 使用 fetch API 的替代方案
// ============================================================================

/*
如果你不想使用 axios，可以使用原生 fetch API：

const API_URL = 'http://localhost:8000/api/users';

// 注册
async function register(data) {
  const response = await fetch(`${API_URL}/register/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include', // 重要：允许带上 Cookie
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(await response.json());
  }

  return response.json();
}

// 登录
async function login(username, password) {
  const response = await fetch(`${API_URL}/login/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    throw new Error(await response.json());
  }

  return response.json();
}
*/
