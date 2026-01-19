import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import Home from '../views/Home.vue'
import Songs from '../views/Songs.vue'
import Charts from '../views/Charts.vue'
import Eval from '../views/Eval.vue'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import Profile from '../views/Profile.vue'
import { getCurrentPhase } from '../api/index.js'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home,
    meta: { title: '首页' }
  },
  {
    path: '/songs',
    name: 'Songs',
    component: Songs,
    meta: { title: '歌曲' }
  },
  {
    path: '/charts',
    name: 'Charts',
    component: Charts,
    meta: { title: '谱面' }
  },
  {
    path: '/eval',
    name: 'Eval',
    component: Eval,
    meta: { title: '评分', requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { title: '登录' }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { title: '注册' }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: Profile,
    meta: { title: '个人中心', requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 缓存当前阶段信息
let currentPhaseCache = null
let phaseCacheTime = 0

/**
 * 获取当前阶段并检查页面访问权限
 */
const checkPageAccess = async (pageName) => {
  // 每 10 秒缓存一次，避免频繁请求
  const now = Date.now()
  if (!currentPhaseCache || (now - phaseCacheTime) > 10000) {
    try {
      currentPhaseCache = await getCurrentPhase()
      phaseCacheTime = now
    } catch (error) {
      console.error('获取阶段信息失败:', error)
      // 返回默认权限：仅允许访问首页
      return true
    }
  }

  const pageAccess = currentPhaseCache?.page_access || {}
  return pageAccess[pageName] !== false
}

/**
 * 获取当前阶段信息（供组件使用）
 */
export const useCurrentPhase = async () => {
  const now = Date.now()
  if (!currentPhaseCache || (now - phaseCacheTime) > 10000) {
    try {
      currentPhaseCache = await getCurrentPhase()
      phaseCacheTime = now
    } catch (error) {
      console.error('获取阶段信息失败:', error)
    }
  }
  return currentPhaseCache
}

// 路由守卫
router.beforeEach(async (to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} -  小妹妹唱歌net` : '小妹妹唱歌net'
  
  // 检查是否需要登录
  if (to.meta.requiresAuth) {
    const token = localStorage.getItem('token')
    if (!token) {
      next({
        path: '/login',
        query: { redirect: to.fullPath }
      })
      return
    }
  }

  // 首页、登录页、注册页直接放行，不检查阶段权限
  const publicPages = ['home', 'login', 'register']
  const routeName = to.name?.toLowerCase() || ''
  
  if (publicPages.includes(routeName)) {
    next()
    return
  }

  // 检查页面访问权限（根据阶段限制）
  const hasAccess = await checkPageAccess(routeName)
  
  if (!hasAccess) {
    const phase = await useCurrentPhase()
    const phaseName = phase?.name || '当前阶段'
    const statusText = phase?.time_remaining || ''
    
    ElMessage({
      type: 'warning',
      message: `此功能将在后续阶段开放。当前阶段：${phaseName} (${statusText})`,
      duration: 3000
    })
    
    // 重定向回首页
    next(false)
    return
  }

  next()
})

export default router
