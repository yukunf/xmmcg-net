import axios from 'axios'
import { ElMessage } from 'element-plus'


// 简单获取 cookie 的方法
const getCookie = (name) => {
  const matches = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()\[\]\\\/\+^])/g, '\\$1') + '=([^;]*)'))
  return matches ? decodeURIComponent(matches[1]) : null
}

const csrfSafeMethod = /^(GET|HEAD|OPTIONS|TRACE)$/i

// 获取 API 基础 URL
const getBaseURL = () => {
  // 如果在开发环境，使用 window.API_BASE_URL（由 main.js 设置）
  if (window.API_BASE_URL) {
    return `${window.API_BASE_URL}/api`
  }
  // 回退到相对路径
  return '/api'
}

// 创建 axios 实例
const api = axios.create({
  baseURL: getBaseURL(),
  timeout: 90000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true  // 允许跨域请求包含凭证
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 始终使用最新的 API 基础地址（避免在模块初始化时拿到错误端口）
    config.baseURL = getBaseURL()

    // 添加 token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // 非安全方法需要携带 CSRF Token
    if (!csrfSafeMethod.test(config.method || '')) {
      const csrfToken = getCookie('csrftoken')
      if (csrfToken) {
        config.headers['X-CSRFToken'] = csrfToken
      }
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
    // 确保已有 CSRF Token
    await ensureCsrfToken()
    const response = await api.post('/users/login/', { username, password })
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 用户注册
 */
export const register = async (username, qqid, email, password, passwordConfirm) => {
  try {
    await ensureCsrfToken()
    const response = await api.post('/users/register/', {
      username,
      qqid,
      email,
      password,
      password_confirm: passwordConfirm
    })
    return response
  } catch (error) {
    // 尝试返回后端的详细错误信息
    if (error.response && error.response.data) {
      const data = error.response.data
      // 后端可能返回 {errors: {...}} 或 {message: ''}
      if (data.errors) {
        // 将错误对象拍平为字符串
        const msg = Object.values(data.errors).flat().join('；')
        throw new Error(msg || '注册失败')
      }
      if (data.message) {
        throw new Error(data.message)
      }
    }
    throw error
  }
}

/**
 * 获取当前登录用户信息
 */
export const getUserProfile = async () => {
  try {
    const response = await api.get('/users/me/')
    return response
  } catch (error) {
    throw error
  }
}



/**
 * 确保已有 CSRF Token（若无则向后端获取并设置 Cookie）
 */
export const ensureCsrfToken = async () => {
  const csrfToken = getCookie('csrftoken')
  if (!csrfToken) {
    try {
      await api.get('/users/csrf/')
    } catch (error) {
      // 忽略错误，交由调用方处理
      throw error
    }
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
    await ensureCsrfToken()
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

/**
 * 获取当前用户的歌曲列表
 */
export const getMySongs = async () => {
  try {
    const response = await api.get('/songs/me/')
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 更新歌曲信息
 */
export const updateSong = async (songId, data) => {
  try {
    await ensureCsrfToken()
    const response = await api.put(`/songs/${songId}/update/`, data)
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 删除歌曲
 */
export const deleteSong = async (songId) => {
  try {
    await ensureCsrfToken()
    const response = await api.delete(`/songs/${songId}/`)
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 获取歌曲详情
 */
export const getSongDetail = async (songId) => {
  try {
    const response = await api.get(`/songs/detail/${songId}/`)
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
 * 获取特定目标的竞标行情
 * @param {Object} params - { song_id: number, chart_id: number, round_id: number }
 */
export const getTargetBids = async (params) => {
  try {
    // 这里的路径会自动拼接 baseURL (/api) 变为 /api/songs/bids/target/
    const response = await api.get('/songs/bids/target/', { params })
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 获取当前用户的竞标列表
 */
export const getMyBids = async (roundId) => {
  try {
    const params = roundId ? { round_id: roundId } : {}
    const response = await api.get('/songs/bids/', { params })
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 提交竞标
 */
export const submitBid = async ({ songId = null, chartId = null, amount, roundId = null }) => {
  try {
    await ensureCsrfToken()
    const data = { amount }
    if (songId) {
      data.song_id = songId
    }
    if (chartId) {
      data.chart_id = chartId
    }
    if (roundId) {
      data.round_id = roundId
    }
    const response = await api.post('/songs/bids/', data)
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 撤回竞标
 */
export const deleteBid = async (bidId) => {
  try {
    await ensureCsrfToken()
    const response = await api.delete(`/songs/bids/${bidId}/`)
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 获取竞标结果（分配结果）
 */
export const getBidResults = async (roundId) => {
  try {
    const params = roundId ? { round_id: roundId } : {}
    const response = await api.get('/songs/bid-results/', { params })
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
 * 获取当前用户的谱面列表
 */
export const getMyCharts = async (roundId) => {
  try {
    const params = roundId ? { bidding_round_id: roundId } : {}
    const response = await api.get('/songs/charts/me/', { params })
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 提交谱面（半成品或完稿）
 */
export const submitChart = async (resultId, formData) => {
  try {
    await ensureCsrfToken()
    const response = await api.post(`/songs/charts/${resultId}/submit/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 下载谱面打包（后端统一打包Zip）
 */
export const downloadChartBundle = async (chartId) => {
  try {
    const response = await api.get(`/songs/charts/${chartId}/bundle/`, {
      responseType: 'blob',
      timeout: 120000, // 大文件下载延长超时
      // 不设置 Accept，避免 DRF 内容协商 406；让服务端直接返回二进制
      withCredentials: false // 该请求不需要会话凭证，避免部分浏览器的跨域凭证限制
    })
    return response
  } catch (error) {
    throw error
  }
}

// ==================== 首页数据 API ====================

/**
 * 获取 Banner 列表
 */
export const getBanners = async () => {
  try {
    const response = await api.get('/songs/banners/')
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 获取公告列表
 */
export const getAnnouncements = async (limit = 10) => {
  try {
    const response = await api.get('/songs/announcements/', { params: { limit } })
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 获取公告列表
 */
export const getAnnouncementsFromAPI = async (limit = 10) => {
  try {
    const response = await api.get(`/songs/announcements/?limit=${limit}`)
    return response
  } catch (error) {
    throw error
  }
}

/**
 * 获取比赛状态
 */
export const getCompetitionStatus = async () => {
  try {
    const response = await api.get('/songs/status/')
    return response
  } catch (error) {
    return {
      currentRound: '未开始',
      status: 'pending',
      statusText: '待开始',
      participants: 0,
      submissions: 0
    }
  }
}

// ==================== 比赛阶段 API ====================

/**
 * 获取所有比赛阶段
 * @param {boolean} includeInactive - 是否包含未激活的阶段，默认为 false
 */
export const getCompetitionPhases = async (includeInactive = false) => {
  try {
    const params = includeInactive ? { include_inactive: 'true' } : {}
    const response = await api.get('/songs/phases/', { params })
    return response
  } catch (error) {
    console.error('获取比赛阶段失败:', error)
    return []
  }
}

/**
 * 获取当前活跃阶段
 */
export const getCurrentPhase = async () => {
  try {
    const response = await api.get('/songs/phase/current/')
    return response
  } catch (error) {
    console.error('获取当前阶段失败:', error)
    // 返回一个默认的阶段对象
    return {
      id: 0,
      name: '未知阶段',
      phase_key: 'unknown',
      status: 'unknown',
      page_access: {
        home: true,
        songs: false,
        charts: false,
        profile: true
      }
    }
  }
}

// ==================== 互评系统相关 API ====================

/**
 * 获取互评配置（包含最大分数和当前轮次）
 */
export const getPeerReviewConfig = async () => {
  try {
    const response = await api.get('/songs/status/')
    return response
  } catch (error) {
    console.error('获取互评配置失败:', error)
    throw error
  }
}

/**
 * 获取我的互评任务列表
 */
export const getMyReviewTasks = async () => {
  try {
    const response = await api.get('/songs/peer-reviews/tasks/')
    return response
  } catch (error) {
    console.error('获取互评任务失败:', error)
    throw error
  }
}


/**
 * 提交互评分数
 */
export const submitReview = async (allocationId, score, comments = '', favorite = false) => {
  try {
    await ensureCsrfToken()
    const response = await api.post(`/songs/peer-reviews/allocations/${allocationId}/submit/`, {
      score: score,
      comment: comments,
      favorite: favorite
    })
    return response
  } catch (error) {
    console.error('提交互评失败:', error)
    throw error
  }
}

/**
 * 提交额外的互评分数（用户自主选择的谱面）
 */
export const submitExtraReview = async (chartId, score, comments = '', favorite = false) => {
  try {
    await ensureCsrfToken()
    const response = await api.post('/songs/peer-reviews/extra/', {
      chart_id: chartId,
      score: score,
      comments: comments,
      favorite: favorite
    })
    return response
  } catch (error) {
    console.error('提交额外互评失败:', error)
    throw error
  }
}

/**
 * 
 * 获取其他用户的公开信息
 */
export const getUserPublicInfo = (userId) => {
  return axios({  
    url: `/api/users/${userId}/public/`, // ⚠️注意：如果没有全局配置baseURL，这里可能要补全 /api 前缀
    method: 'get'
    // 如果需要 token，通常 axios 拦截器会处理；如果没有拦截器，可能还需要 headers: { ... }
  })
}