<template>
  <el-menu
    :default-active="activeIndex"
    mode="horizontal"
    :ellipsis="false"
    @select="handleSelect"
    class="navbar"
  >
    <div class="logo">
      <el-icon size="24"><Trophy /></el-icon>
      <span class="logo-text">XMMCG</span>
    </div>
    
    <div class="flex-grow" />
    
    <el-menu-item index="/">首页</el-menu-item>
    <el-menu-item index="/songs">歌曲</el-menu-item>
    <el-menu-item index="/charts">谱面</el-menu-item>
    
    <div class="flex-grow" />
    
    <div v-if="!isLoggedIn" class="auth-buttons">
      <el-button type="primary" size="small" @click="$router.push('/login')">
        登录
      </el-button>
      <el-button type="success" size="small" @click="$router.push('/register')">
        注册
      </el-button>
    </div>
    
    <el-sub-menu v-else index="user" class="user-menu">
      <template #title>
        <el-icon><UserFilled /></el-icon>
        <span>{{ username }}</span>
      </template>
      <el-menu-item index="/profile">
        <el-icon><User /></el-icon>
        个人中心
      </el-menu-item>
      <el-menu-item @click="handleLogout">
        <el-icon><SwitchButton /></el-icon>
        退出登录
      </el-menu-item>
    </el-sub-menu>
  </el-menu>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Trophy, UserFilled, User, SwitchButton } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()

const activeIndex = ref('/')
const username = ref(localStorage.getItem('username') || '')
const isLoggedIn = computed(() => !!localStorage.getItem('token'))

// 监听路由变化，更新激活菜单项
watch(() => route.path, (newPath) => {
  activeIndex.value = newPath
}, { immediate: true })

const handleSelect = (key) => {
  if (key !== 'user') {
    router.push(key)
  }
}

const handleLogout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  username.value = ''
  ElMessage.success('已退出登录')
  router.push('/')
}
</script>

<style scoped>
.navbar {
  position: sticky;
  top: 0;
  z-index: 1000;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px;
  font-size: 20px;
  font-weight: bold;
  color: #409EFF;
  cursor: pointer;
}

.logo-text {
  margin-left: 5px;
}

.flex-grow {
  flex-grow: 1;
}

.auth-buttons {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px;
}

.user-menu {
  margin-left: auto;
}

@media (max-width: 768px) {
  .logo-text {
    display: none;
  }
  
  .auth-buttons {
    gap: 5px;
    padding: 0 10px;
  }
}
</style>
