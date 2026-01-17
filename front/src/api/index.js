import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建 axios 实例
const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 添加 token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    if (error.response) {
      switch (error.response.status) {
        case 401:
          ElMessage.error('未授权，请重新登录')
          localStorage.removeItem('token')
          localStorage.removeItem('username')
          window.location.href = '/login'
          break
        case 403:
          ElMessage.error('没有权限访问')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器错误')
          break
        default:
          ElMessage.error(error.response.data.message || '请求失败')
      }
    } else {
      ElMessage.error('网络错误，请检查您的网络连接')
    }
    return Promise.reject(error)
  }
)

// ==================== 用户认证 API ====================

/**
 * 用户登录
 */
export const login = async (username, password) => {
  try {
    const response = await api.post('/users/login/', { username, password })
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 用户注册
 */
export const register = async (username, password) => {
  try {
    const response = await api.post('/users/register/', { username, password })
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 获取用户信息
 */
export const getUserProfile = async () => {
  try {
    const response = await api.get('/users/profile/')
    return response
  } catch (error) {
    throw error
  }
}

// ==================== 歌曲 API ====================

/**
 * 获取歌曲列表
 */
export const getSongs = async (params = {}) => {
  try {
    const response = await api.get('/songs/', { params })
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 上传歌曲
 */
export const uploadSong = async (formData) => {
  try {
    const response = await api.post('/songs/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response
  } catch (error) {
    throw error
  }
}

// ==================== 竞标 API ====================

/**
 * 获取竞标轮次列表
 */
export const getBiddingRounds = async () => {
  try {
    const response = await api.get('/songs/bidding-rounds/')
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 提交竞标
 */
export const submitBid = async (roundId, songId, amount) => {
  try {
    const response = await api.post(`/songs/bidding-rounds/${roundId}/bid/`, {
      song_id: songId,
      amount
    })
    return response
  } catch (error) {
    throw error
  }
}

// ==================== 谱面 API ====================

/**
 * 获取谱面列表
 */
export const getCharts = async (params = {}) => {
  try {
    const response = await api.get('/songs/charts/', { params })
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 提交谱面
 */
export const submitChart = async (data) => {
  try {
    const response = await api.post('/songs/charts/', data)
    return response
  } catch (error) {
    throw error
  }
}

// ==================== 首页数据 API ====================

/**
 * 获取比赛状态
 */
export const getCompetitionStatus = async () => {
  try {
    const response = await api.get('/songs/status/')
    return response
  } catch (error) {
    // 如果接口不存在，返回模拟数据
    return {
      currentRound: '第一轮',
      status: 'active',
      statusText: '进行中',
      participants: 0,
      submissions: 0
    }
  }
}

/**
 * 获取公告列表
 */
export const getAnnouncements = async () => {
  try {
    const response = await api.get('/songs/announcements/')
    return response
  } catch (error) {
    // 如果接口不存在，返回空数组
    return []
  }
}

export default api
