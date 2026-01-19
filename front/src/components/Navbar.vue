<template>
  <!-- 桌面端导航栏 -->
  <el-menu
    v-if="!isMobile"
    :default-active="activeIndex"
    mode="horizontal"
    :ellipsis="false"
    @select="handleSelect"
    class="navbar"
  >
    <div class="logo">
      <img src="/res/xmmcglogo.png" alt="XMMCG Logo" height="32" />
    </div>
    
    <div class="flex-grow" />
    
    <el-menu-item index="/">首页</el-menu-item>
    
    <!-- 根据阶段权限动态显示菜单项 -->
    <el-menu-item 
      index="/songs"
      :disabled="!pageAccess.songs"
      :class="{ 'disabled-menu-item': !pageAccess.songs }"
    >
      歌曲
      <el-tooltip v-if="!pageAccess.songs" content="此功能在竞标期开放" placement="bottom">
        <el-icon size="16" style="margin-left: 4px;"><Warning /></el-icon>
      </el-tooltip>
    </el-menu-item>
    
    <el-menu-item 
      index="/charts"
      :disabled="!pageAccess.charts"
      :class="{ 'disabled-menu-item': !pageAccess.charts }"
    >
      谱面
      <el-tooltip v-if="!pageAccess.charts" content="此功能在制谱期开放" placement="bottom">
        <el-icon size="16" style="margin-left: 4px;"><Warning /></el-icon>
      </el-tooltip>
    </el-menu-item>
    
    <el-menu-item 
      index="/eval"
      :disabled="!pageAccess.eval"
      :class="{ 'disabled-menu-item': !pageAccess.eval }"
    >
      评分
      <el-tooltip v-if="!pageAccess.eval" content="此功能在互评期开放" placement="bottom">
        <el-icon size="16" style="margin-left: 4px;"><Warning /></el-icon>
      </el-tooltip>
    </el-menu-item>
    
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
      <el-menu-item index="logout" @click="handleLogout">
        <el-icon><SwitchButton /></el-icon>
        退出登录
      </el-menu-item>
    </el-sub-menu>
  </el-menu>

  <!-- 移动端导航栏 -->
  <div v-else class="mobile-navbar">
    <div class="mobile-header">
      <div class="logo" @click="$router.push('/')">
        <img src="/res/xmmcglogo.png" alt="XMMCG Logo" height="24" />
      </div>
      
      <div class="mobile-actions">
        <template v-if="!isLoggedIn">
          <el-button 
            type="primary" 
            size="small" 
            @click="$router.push('/login')"
          >
            登录
          </el-button>
          <el-button 
            type="success" 
            size="small" 
            @click="$router.push('/register')"
          >
            注册
          </el-button>
        </template>
        <template v-else>
          <el-button 
            circle 
            size="small"
            @click="showMobileMenu = !showMobileMenu"
          >
            <el-icon><UserFilled /></el-icon>
          </el-button>
        </template>
        <el-button 
          circle 
          size="small"
          @click="mobileDrawerVisible = true"
        >
          <el-icon><Menu /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 移动端抽屉菜单 -->
    <el-drawer
      v-model="mobileDrawerVisible"
      direction="rtl"
      size="70%"
      :show-close="false"
    >
      <template #header>
        <div class="drawer-header">
          <el-icon :size="24"><Trophy /></el-icon>
          <span>菜单</span>
        </div>
      </template>
      
      <el-menu
        :default-active="activeIndex"
        @select="handleMobileSelect"
        class="mobile-menu"
      >
        <el-menu-item index="/">
          <el-icon><HomeFilled /></el-icon>
          <span>首页</span>
        </el-menu-item>
        
        <el-menu-item 
          index="/songs"
          :disabled="!pageAccess.songs"
        >
          <el-icon><Headset /></el-icon>
          <span>歌曲</span>
          <el-icon v-if="!pageAccess.songs" style="margin-left: auto;"><Warning /></el-icon>
        </el-menu-item>
        
        <el-menu-item 
          index="/charts"
          :disabled="!pageAccess.charts"
        >
          <el-icon><Document /></el-icon>
          <span>谱面</span>
          <el-icon v-if="!pageAccess.charts" style="margin-left: auto;"><Warning /></el-icon>
        </el-menu-item>
        
        <el-menu-item 
          index="/eval"
          :disabled="!pageAccess.eval"
        >
          <el-icon><Star /></el-icon>
          <span>评分</span>
          <el-icon v-if="!pageAccess.eval" style="margin-left: auto;"><Warning /></el-icon>
        </el-menu-item>
        
        <el-divider v-if="isLoggedIn" />
        
        <el-menu-item v-if="isLoggedIn" index="/profile">
          <el-icon><User /></el-icon>
          <span>个人中心</span>
        </el-menu-item>
        
        <el-menu-item v-if="isLoggedIn" index="logout" @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
          <span>退出登录</span>
        </el-menu-item>
        
        <el-menu-item v-if="!isLoggedIn" index="/register" @click="handleMobileSelect('/register')">
          <el-icon><UserFilled /></el-icon>
          <span>注册</span>
        </el-menu-item>
      </el-menu>
    </el-drawer>

    <!-- 移动端用户菜单（快捷弹窗） -->
    <el-dialog
      v-model="showMobileMenu"
      width="80%"
      :show-close="false"
      class="mobile-user-dialog"
    >
      <template #header>
        <div class="mobile-user-header">
          <el-icon><UserFilled /></el-icon>
          <span>{{ username }}</span>
        </div>
      </template>
      <div class="mobile-user-actions">
        <el-button type="primary" @click="handleMobileSelect('/profile')" block>
          <el-icon><User /></el-icon>
          个人中心
        </el-button>
        <el-button type="danger" @click="handleLogout" block>
          <el-icon><SwitchButton /></el-icon>
          退出登录
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { 
  Trophy, UserFilled, User, SwitchButton, Warning, Menu,
  HomeFilled, Headset, Document, Star
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useCurrentPhase } from '../router/index.js'

const router = useRouter()
const route = useRoute()

const activeIndex = ref('/')
const username = ref(localStorage.getItem('username') || '')
const isLoggedIn = computed(() => !!localStorage.getItem('token'))
const isMobile = ref(false)
const mobileDrawerVisible = ref(false)
const showMobileMenu = ref(false)

const pageAccess = ref({
  home: true,
  songs: true,
  charts: true,
  eval: true,
  profile: true
})

// 检测屏幕尺寸
const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768
}

// 监听路由变化，更新激活菜单项
watch(() => route.path, (newPath) => {
  activeIndex.value = newPath
}, { immediate: true })

const loadPhasePermissions = async () => {
  try {
    const phase = await useCurrentPhase()
    if (phase?.page_access) {
      pageAccess.value = phase.page_access
    }
  } catch (error) {
    console.error('加载阶段权限失败:', error)
  }
}

const handleSelect = (key) => {
  if (key !== 'user') {
    // 检查权限
    const routePermissions = {
      '/songs': pageAccess.value.songs,
      '/charts': pageAccess.value.charts,
      '/eval': pageAccess.value.eval,
      '/profile': pageAccess.value.profile
    }
    
    if (routePermissions[key] === false) {
      ElMessage.warning('此功能在当前阶段不可用')
      return
    }
    
    router.push(key)
  }
}

const handleMobileSelect = (key) => {
  mobileDrawerVisible.value = false
  showMobileMenu.value = false
  handleSelect(key)
}

const handleLogout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  username.value = ''
  mobileDrawerVisible.value = false
  showMobileMenu.value = false
  ElMessage.success('已退出登录')
  router.push('/')
}

onMounted(() => {
  loadPhasePermissions()
  checkMobile()
  window.addEventListener('resize', checkMobile)
  
  // 每 30 秒刷新权限
  setInterval(() => {
    loadPhasePermissions()
  }, 30000)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<style scoped>
/* 桌面端导航栏 */
.navbar {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: var(--surface-strong);
  backdrop-filter: blur(var(--glass-blur));
  border-bottom: 1px solid var(--border-color);
  box-shadow: var(--shadow-elevated);
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px;
  font-size: 20px;
  font-weight: bold;
  color: var(--primary-color);
  cursor: pointer;
}

.logo img {
  height: 32px;
  width: auto;
}

/* 移动端Logo优化 */
.mobile-navbar .logo {
  padding: 0;
}

.mobile-navbar .logo img {
  height: 24px;
  width: auto;
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

.disabled-menu-item {
  opacity: 0.6;
  cursor: not-allowed;
}

.disabled-menu-item:hover {
  background-color: transparent !important;
}

/* 移动端导航栏 */
.mobile-navbar {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: var(--surface-strong);
  backdrop-filter: blur(var(--glass-blur));
  border-bottom: 1px solid var(--border-color);
  box-shadow: var(--shadow-elevated);
}

.mobile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  min-height: 60px;
}

.mobile-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.mobile-actions .el-button--small {
  padding: 6px 12px;
  font-size: 13px;
  min-width: 48px;
}

.drawer-header {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  font-weight: bold;
  color: var(--primary-color);
}

/* 移动端菜单 - 确保文字和图标可见 */
.mobile-menu {
  border: none !important;
  background: var(--surface-color) !important;
}

.mobile-menu :deep(.el-menu) {
  background: var(--surface-color) !important;
}

/* 菜单项基础样式 */
.mobile-menu :deep(.el-menu__item) {
  height: 56px !important;
  line-height: 56px !important;
  font-size: 16px !important;
  padding: 0 20px !important;
  display: flex !important;
  align-items: center !important;
  background: var(--surface-color) !important;
  color: var(--text-primary) !important;
  border: none !important;
}

/* 菜单项中的文字 */
.mobile-menu :deep(.el-menu__item) span {
  color: var(--text-primary) !important;
  font-size: 16px !important;
}

/* 菜单项中的图标 */
.mobile-menu :deep(.el-menu__item .el-icon) {
  color: var(--text-primary) !important;
  font-size: 20px !important;
  margin-right: 12px !important;
}

.mobile-menu :deep(.el-menu__item svg) {
  fill: var(--text-primary) !important;
  color: var(--text-primary) !important;
  width: 1em !important;
  height: 1em !important;
}

/* 菜单项悬停态 */
.mobile-menu :deep(.el-menu__item:hover) {
  background-color: rgba(122, 200, 255, 0.15) !important;
  color: var(--primary-color) !important;
}

.mobile-menu :deep(.el-menu__item:hover svg) {
  fill: var(--primary-color) !important;
  color: var(--primary-color) !important;
}

/* 菜单项激活态 */
.mobile-menu :deep(.el-menu__item.is-active) {
  background-color: rgba(122, 200, 255, 0.2) !important;
  color: var(--primary-color) !important;
}

.mobile-menu :deep(.el-menu__item.is-active svg) {
  fill: var(--primary-color) !important;
  color: var(--primary-color) !important;
}

.mobile-user-header {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 18px;
  font-weight: bold;
}

.mobile-user-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mobile-user-actions .el-button {
  height: 48px;
  font-size: 16px;
}

/* 移动端对话框样式调整 */
:deep(.mobile-user-dialog) {
  border-radius: 12px;
}

:deep(.mobile-user-dialog .el-dialog__header) {
  padding: 20px;
  border-bottom: 1px solid #eee;
}

:deep(.mobile-user-dialog .el-dialog__body) {
  padding: 20px;
}

/* 移动端抽屉样式 */
:deep(.el-drawer) {
  background: var(--surface-color) !important;
}

:deep(.el-drawer__header) {
  margin-bottom: 16px;
  padding: 20px;
  border-bottom: 1px solid var(--border-color);
  background: var(--surface-color) !important;
}

:deep(.el-drawer__body) {
  padding: 0 !important;
  background: var(--surface-color) !important;
}
</style>
