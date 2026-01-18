<template>
  <div class="songs-page">
    <el-container>
      <el-main>
        <!-- 1. 上传歌曲组件 -->
        <el-card class="upload-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Upload /></el-icon>
              <span>上传歌曲</span>
              <el-tag v-if="mySongs.length > 0" type="info" size="small">
                已上传 {{ mySongs.length }}/2 首
              </el-tag>
            </div>
          </template>

          <el-form 
            ref="uploadFormRef" 
            :model="uploadForm" 
            :rules="uploadRules" 
            label-width="100px"
            :disabled="uploading || mySongs.length >= 2"
          >
            <el-form-item label="音频文件" prop="audioFile">
              <el-upload
                ref="audioUploadRef"
                :auto-upload="false"
                :limit="1"
                :on-change="handleAudioChange"
                :on-remove="handleAudioRemove"
                accept=".mp3"
                :file-list="audioFileList"
              >
                <el-button type="primary" :icon="Upload">选择MP3文件</el-button>
                <template #tip>
                  <div class="el-upload__tip">
                    仅支持 MP3 格式，文件大小不超过 10MB
                  </div>
                </template>
              </el-upload>
            </el-form-item>

            <el-form-item v-if="showTitleField" label="歌曲标题" prop="title">
              <el-input 
                v-model="uploadForm.title" 
                placeholder="请输入或编辑歌曲标题（最多100字符）"
                maxlength="100"
                show-word-limit
              />
              <div class="title-hint" v-if="uploadForm.title">
                <el-text type="success" size="small">✓ 已从MP3文件读取标题</el-text>
              </div>
            </el-form-item>

            <el-form-item label="封面图片" prop="coverImage">
              <el-upload
                ref="coverUploadRef"
                :auto-upload="false"
                :limit="1"
                :on-change="handleCoverChange"
                :on-remove="handleCoverRemove"
                accept=".jpg,.jpeg,.png"
                :file-list="coverFileList"
                list-type="picture"
              >
                <el-button :icon="Picture">选择封面</el-button>
                <template #tip>
                  <div class="el-upload__tip">
                    支持 JPG、PNG 格式，文件大小不超过 2MB（可选）
                  </div>
                </template>
              </el-upload>
            </el-form-item>

            <el-form-item label="歌曲链接" prop="neteaseUrl">
              <el-input 
                v-model="uploadForm.neteaseUrl" 
                placeholder="网易云音乐链接（可选）"
                type="url"
              />
            </el-form-item>

            <el-form-item>
              <el-button 
                type="primary" 
                @click="handleUpload"
                :loading="uploading"
                :disabled="mySongs.length >= 2"
              >
                {{ uploading ? '上传中...' : '上传歌曲' }}
              </el-button>
              <el-button @click="resetUploadForm">重置</el-button>
              <el-text v-if="mySongs.length >= 2" type="warning" size="small">
                已达到上传上限，如需上传新歌曲请先删除旧歌曲
              </el-text>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 2. 我的竞标组件 -->
        <el-card class="bids-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><TrophyBase /></el-icon>
              <span>我的竞标</span>
              <el-button 
                size="small" 
                type="primary" 
                :icon="Refresh" 
                @click="loadMyBids"
                circle
              />
            </div>
          </template>

          <div v-if="bidsLoading" class="loading-container">
            <el-skeleton :rows="3" animated />
          </div>

          <el-empty 
            v-else-if="!currentBidRound" 
            description="当前没有活跃的竞标轮次"
            :image-size="120"
          />

          <div v-else>
            <el-alert 
              :title="`当前轮次：${currentBidRound.name}`" 
              type="info" 
              :closable="false"
              class="round-info"
            >
              <template #default>
                已竞标 {{ myBids.length }}/{{ maxBids }} 首
              </template>
            </el-alert>

            <el-empty 
              v-if="myBids.length === 0" 
              description="您还没有竞标任何歌曲"
              :image-size="120"
            >
              <el-button type="primary" @click="scrollToSongs">去浏览歌曲</el-button>
            </el-empty>

            <el-table v-else :data="myBids" stripe style="width: 100%">
              <el-table-column prop="song.title" label="歌曲标题" min-width="200" />
              <el-table-column prop="amount" label="竞标金额" width="120">
                <template #default="{ row }">
                  <el-tag type="warning">{{ row.amount }} Token</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="120">
                <template #default="{ row }">
                  <el-tag 
                    :type="getBidStatusType(row.status)"
                    :effect="row.status === 'won' ? 'dark' : 'plain'"
                  >
                    {{ getBidStatusText(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="竞标时间" width="180">
                <template #default="{ row }">
                  {{ formatDate(row.created_at) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120" align="center">
                <template #default="{ row }">
                  <el-button
                    v-if="row.status === 'won'"
                    type="success"
                    size="small"
                    :icon="Download"
                    @click="downloadSong(row.song)"
                  >
                    下载
                  </el-button>
                  <span v-else style="color: #ccc; font-size: 12px;">-</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>

        <!-- 3. 浏览歌曲组件 -->
        <el-card class="songs-list-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Headset /></el-icon>
              <span>所有歌曲</span>
              <div class="header-actions">
                <el-select 
                  v-model="cardSize" 
                  placeholder="显示模式" 
                  style="width: 120px; margin-right: 10px;"
                >
                  <el-option label="小卡片" value="small" />
                  <el-option label="中卡片" value="medium" />
                  <el-option label="列表" value="list" />
                </el-select>
                <el-select 
                  v-model="sortBy" 
                  placeholder="排序方式" 
                  style="width: 120px; margin-right: 10px;"
                >
                  <el-option label="标题排序" value="title" />
                  <el-option label="时间排序" value="date" />
                </el-select>
                <el-input
                  v-model="searchKeyword"
                  placeholder="搜索歌曲标题"
                  :prefix-icon="Search"
                  clearable
                  style="width: 200px; margin-right: 10px;"
                />
                <el-button 
                  type="primary" 
                  :icon="Refresh" 
                  @click="loadSongs"
                  circle
                />
              </div>
            </div>
          </template>

          <div v-if="songsLoading" class="loading-container">
            <el-skeleton :rows="5" animated />
          </div>

          <el-empty 
            v-else-if="filteredSongs.length === 0" 
            description="暂无歌曲"
            :image-size="200"
          />

          <div v-else class="songs-grid" :class="`grid-${cardSize}`">
            <el-card
              v-for="song in paginatedSongs"
              :key="song.id"
              class="song-card"
              :class="`card-${cardSize}`"
              :body-style="{ padding: '0' }"
              shadow="hover"
            >
              <!-- 列表模式 -->
              <div v-if="cardSize === 'list'" class="list-item">
                <div class="list-cover" @click="toggleExpand(song.id)">
                  <img 
                    v-if="song.cover_url" 
                    :src="getFullImageUrl(song.cover_url)" 
                    :alt="song.title"
                    @error="handleImageError"
                  />
                  <div v-else class="cover-placeholder-small">
                    <el-icon :size="24"><Headset /></el-icon>
                  </div>
                </div>

                <div class="list-info" @click="toggleExpand(song.id)" :title="expandedSongs.includes(song.id) ? '点击收起详情' : '点击展开详情和操作'">
                  <div class="list-title">{{ song.title }}</div>
                  <div class="list-date">
                    <el-icon :size="12"><Clock /></el-icon>
                    {{ formatDate(song.created_at).split(' ')[0] }}
                  </div>
                </div>

                <div v-show="expandedSongs.includes(song.id)" class="list-actions">
                  <el-button 
                    type="primary" 
                    size="small"
                    :icon="Download"
                    @click="downloadSong(song)"
                  >
                    下载
                  </el-button>
                  <template v-if="isMyOwnSong(song)">
                    <el-button 
                      type="warning" 
                      size="small"
                      :icon="Edit"
                      @click="editSong(song)"
                    >
                      编辑
                    </el-button>
                  </template>
                </div>
              </div>

              <!-- 卡片模式 -->
              <div v-else class="card-item">
                <!-- 卡片封面 -->
                <div class="song-cover" @click="toggleExpand(song.id)" :title="expandedSongs.includes(song.id) ? '点击收起详情' : '点击展开详情和操作'">
                  <img 
                    v-if="song.cover_url" 
                    :src="getFullImageUrl(song.cover_url)" 
                    :alt="song.title"
                    @error="handleImageError"
                  />
                  <div v-else class="cover-placeholder">
                    <el-icon :size="60"><Headset /></el-icon>
                  </div>
                  <div class="cover-overlay">
                    <el-icon :size="30">
                      <CaretRight v-if="!expandedSongs.includes(song.id)" />
                      <CaretBottom v-else />
                    </el-icon>
                    <div class="overlay-text" v-if="!expandedSongs.includes(song.id)">
                      点击查看详情
                    </div>
                  </div>
                </div>

                <!-- 卡片标题 -->
                <div class="song-title" @click="toggleExpand(song.id)" :title="expandedSongs.includes(song.id) ? '点击收起详情' : '点击展开详情和操作'">
                  <h3>{{ song.title }}</h3>
                  <p class="song-meta">
                    <el-icon><Clock /></el-icon>
                    <span class="meta-text">{{ formatDate(song.created_at).split(' ')[0] }}</span>
                  </p>
                </div>

                <!-- 展开内容 -->
                <el-collapse-transition>
                  <div v-show="expandedSongs.includes(song.id)" class="song-details">
                    <el-divider />
                    
                    <div class="detail-item">
                      <el-text type="info">上传时间：</el-text>
                      <el-text>{{ formatDate(song.created_at) }}</el-text>
                    </div>

                    <div class="detail-item" v-if="song.netease_url">
                      <el-button 
                        type="primary" 
                        size="small"
                        :icon="Link"
                        @click="openNeteaseUrl(song.netease_url)"
                      >
                        打开网易云链接
                      </el-button>
                    </div>

                    <div class="detail-actions">
                      <el-button 
                        type="primary" 
                        :icon="Download"
                        @click="downloadSong(song)"
                      >
                        下载音频
                      </el-button>
                      
                      <!-- 如果是自己的歌曲，显示管理按钮 -->
                      <template v-if="isMyOwnSong(song)">
                        <el-button 
                          type="warning" 
                          :icon="Edit"
                          @click="editSong(song)"
                        >
                          编辑
                        </el-button>
                      </template>

                      <!-- 竞标按钮 -->
                      <el-button 
                        type="success" 
                        :icon="TrophyBase"
                        @click="showBidDialog(song)"
                      >
                        竞标
                      </el-button>
                    </div>
                  </div>
                </el-collapse-transition>
              </div>
            </el-card>
          </div>

          <!-- 分页 -->
          <el-pagination
            v-if="filteredSongs.length > pageSizeByMode"
            v-model:current-page="currentPage"
            v-model:page-size="pageSizeByMode"
            :page-sizes="cardSize === 'list' ? [20, 30, 50, 100] : [8, 12, 20, 40]"
            :total="filteredSongs.length"
            layout="total, sizes, prev, pager, next, jumper"
            class="pagination"
            @current-change="handlePageChange"
            @size-change="handleSizeChange"
          />
        </el-card>
      </el-main>
    </el-container>

    <!-- 编辑歌曲对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑歌曲信息"
      width="500px"
    >
      <el-form 
        ref="editFormRef"
        :model="editForm" 
        label-width="100px"
      >
        <el-form-item label="歌曲标题">
          <el-input v-model="editForm.title" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="歌曲链接">
          <el-input v-model="editForm.netease_url" type="url" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpdateSong" :loading="updating">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 竞标对话框 -->
    <el-dialog
      v-model="bidDialogVisible"
      title="提交竞标"
      width="450px"
    >
      <el-form
        :model="bidForm"
        label-width="80px"
      >
        <el-form-item label="歌曲">
          <el-text>{{ bidForm.songTitle }}</el-text>
        </el-form-item>
        
        <el-form-item label="竞标轮次">
          <el-text v-if="currentRound">
            {{ currentRound.name }}
          </el-text>
        </el-form-item>
        
        <el-divider />
        
        <el-form-item label="代币余额">
          <el-tag type="info">{{ userToken }} 代币</el-tag>
        </el-form-item>
        
        <el-form-item label="已竞标">
          <el-text>
            {{ myBidsCount }} / {{ maxBids }}
          </el-text>
        </el-form-item>
        
        <el-divider />
        
        <el-form-item label="出价" prop="amount">
          <el-input-number
            v-model="bidForm.amount"
            :min="1"
            :max="Math.max(1, userToken)"
            placeholder="输入竞标金额"
            style="width: 100%"
          />
        </el-form-item>
        
        <el-alert
          v-if="bidForm.amount && bidForm.amount > userToken"
          title="代币不足"
          type="error"
          :closable="false"
          style="margin-bottom: 10px"
        />
        
        <el-alert
          v-if="myBidsCount >= maxBids"
          title="已达到竞标数量限制"
          type="warning"
          :closable="false"
          style="margin-bottom: 10px"
        />
      </el-form>
      
      <template #footer>
        <el-button @click="bidDialogVisible = false">取消</el-button>
        <el-button 
          type="success" 
          @click="handleSubmitBid" 
          :loading="bidSubmitting"
          :disabled="!bidForm.amount || bidForm.amount > userToken || myBidsCount >= maxBids"
        >
          提交竞标
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Upload, Picture, Headset, TrophyBase, Refresh, Search, 
  Download, Edit, Delete, User, CaretRight, CaretBottom, Clock, Link 
} from '@element-plus/icons-vue'
import { 
  getSongs, uploadSong, getMySongs, updateSong, deleteSong,
  getMyBids, getBiddingRounds, submitBid, getUserProfile
} from '@/api'
import { parseBlob } from 'music-metadata'

// 用户信息
const currentUser = ref(null)

// 上传表单
const uploadFormRef = ref(null)
const audioUploadRef = ref(null)
const coverUploadRef = ref(null)
const uploading = ref(false)
const showTitleField = ref(false)
const uploadForm = ref({
  title: '',
  audioFile: null,
  coverImage: null,
  neteaseUrl: ''
})
const audioFileList = ref([])
const coverFileList = ref([])

// 验证URL格式
const validateUrl = (rule, value, callback) => {
  if (!value) {
    callback()
    return
  }
  try {
    new URL(value)
    callback()
  } catch {
    callback(new Error('请输入有效的URL地址'))
  }
}

const uploadRules = {
  title: [
    { required: true, message: '请输入歌曲标题', trigger: 'blur' },
    { min: 1, max: 100, message: '标题长度在 1 到 100 个字符', trigger: 'blur' }
  ],
  audioFile: [
    { required: true, message: '请选择音频文件', trigger: 'change' }
  ],
  neteaseUrl: [
    { validator: validateUrl, trigger: 'blur' }
  ]
}

// 我的歌曲
const mySongs = ref([])

// 竞标相关
const bidsLoading = ref(false)
const currentBidRound = ref(null)
const myBids = ref([])
const maxBids = ref(5)

// 歌曲列表
const songsLoading = ref(false)
const allSongs = ref([])
const expandedSongs = ref([])
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(12)
const cardSize = ref('medium') // small, medium, list
const sortBy = ref('date') // title, date

// 计算属性：根据模式调整每页数量
const pageSizeByMode = computed(() => {
  if (cardSize.value === 'list') {
    return 30 // 列表模式显示更多项
  }
  return pageSize.value
})

// 编辑对话框
const editDialogVisible = ref(false)
const editFormRef = ref(null)
const editForm = ref({
  id: null,
  title: '',
  netease_url: ''
})
const updating = ref(false)

// 竞标对话框
const bidDialogVisible = ref(false)
const bidForm = ref({
  songId: null,
  songTitle: '',
  amount: null
})
const bidSubmitting = ref(false)
const userToken = ref(0)
const currentRound = ref(null)
const myBidsCount = ref(0)

// 计算属性：过滤后的歌曲
const filteredSongs = computed(() => {
  let songs = allSongs.value
  
  // 搜索过滤
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    songs = songs.filter(song => 
      song.title.toLowerCase().includes(keyword)
    )
  }
  
  // 排序
  const sorted = [...songs]
  if (sortBy.value === 'title') {
    // 按标题升序（A-Z），支持多语言
    sorted.sort((a, b) => {
      return a.title.localeCompare(b.title, 'zh-CN', { sensitivity: 'accent' })
    })
  } else if (sortBy.value === 'date') {
    // 按最近时间排序（降序，最新的在前）
    sorted.sort((a, b) => {
      const dateA = new Date(a.created_at).getTime()
      const dateB = new Date(b.created_at).getTime()
      return dateB - dateA
    })
  }
  
  return sorted
})

// 计算属性：分页后的歌曲
const paginatedSongs = computed(() => {
  const start = (currentPage.value - 1) * pageSizeByMode.value
  const end = start + pageSizeByMode.value
  return filteredSongs.value.slice(start, end)
})

// 文件选择处理
const handleAudioChange = (file) => {
  // 验证文件大小
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('音频文件大小不能超过 10MB')
    audioFileList.value = []
    uploadForm.value.audioFile = null
    showTitleField.value = false
    return
  }
  // 验证文件格式
  if (!file.name.toLowerCase().endsWith('.mp3')) {
    ElMessage.error('仅支持 MP3 格式')
    audioFileList.value = []
    uploadForm.value.audioFile = null
    showTitleField.value = false
    return
  }
  
  uploadForm.value.audioFile = file.raw
  audioFileList.value = [file]
  
  // 读取MP3元数据
  extractMP3Title(file.raw)
}

const handleAudioRemove = () => {
  uploadForm.value.audioFile = null
  audioFileList.value = []
  uploadForm.value.title = ''
  showTitleField.value = false
}

// 提取MP3标题
const extractMP3Title = async (file) => {
  try {
    const metadata = await parseBlob(file)
    let title = metadata.common?.title || ''
    
    if (title) {
      uploadForm.value.title = title
      showTitleField.value = true
      ElMessage.success(`已读取标题: ${title}`)
    } else {
      showTitleField.value = true
      ElMessage.info('MP3文件中未找到标题，请手动输入')
    }
  } catch (error) {
    console.warn('读取MP3标题失败:', error)
    // 即使读取失败，也显示标题字段让用户手动输入
    showTitleField.value = true
    ElMessage.warning('无法自动读取MP3标题，请手动输入')
  }
}

const handleCoverChange = (file) => {
  // 验证文件大小
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.error('封面图片大小不能超过 2MB')
    coverFileList.value = []
    uploadForm.value.coverImage = null
    return
  }
  // 验证文件格式
  const ext = file.name.split('.').pop().toLowerCase()
  if (!['jpg', 'jpeg', 'png'].includes(ext)) {
    ElMessage.error('仅支持 JPG、PNG 格式')
    coverFileList.value = []
    uploadForm.value.coverImage = null
    return
  }
  uploadForm.value.coverImage = file.raw
  coverFileList.value = [file]
}

const handleCoverRemove = () => {
  uploadForm.value.coverImage = null
  coverFileList.value = []
}

// 上传歌曲
const handleUpload = async () => {
  if (!uploadFormRef.value) return
  
  await uploadFormRef.value.validate(async (valid) => {
    if (!valid) {
      return
    }

    if (!uploadForm.value.audioFile) {
      ElMessage.error('请选择音频文件')
      return
    }

    uploading.value = true
    try {
      const formData = new FormData()
      formData.append('title', uploadForm.value.title)
      formData.append('audio_file', uploadForm.value.audioFile)
      if (uploadForm.value.coverImage) {
        formData.append('cover_image', uploadForm.value.coverImage)
      }
      if (uploadForm.value.neteaseUrl) {
        formData.append('netease_url', uploadForm.value.neteaseUrl)
      }

      const response = await uploadSong(formData)
      if (response.success) {
        ElMessage.success(response.message || '上传成功')
        resetUploadForm()
        await loadMySongs()
        await loadSongs()
        // 上传成功后刷新用户信息（更新歌曲计数）
        try {
          await getUserProfile()
        } catch (e) {
          console.warn('刷新用户信息失败:', e)
        }
      }
    } catch (error) {
      console.error('上传失败:', error)
      ElMessage.error(error.response?.data?.message || '上传失败')
    } finally {
      uploading.value = false
    }
  })
}

// 重置上传表单
const resetUploadForm = () => {
  uploadForm.value = {
    title: '',
    audioFile: null,
    coverImage: null,
    neteaseUrl: ''
  }
  audioFileList.value = []
  coverFileList.value = []
  showTitleField.value = false
  uploadFormRef.value?.resetFields()
}

// 加载我的歌曲
const loadMySongs = async () => {
  try {
    const response = await getMySongs()
    if (response.success) {
      mySongs.value = response.songs || []
      console.log('加载的我的歌曲:', mySongs.value)
    }
  } catch (error) {
    console.error('加载我的歌曲失败:', error)
  }
}

// 加载我的竞标
const loadMyBids = async () => {
  bidsLoading.value = true
  try {
    const response = await getMyBids()
    if (response.success) {
      currentBidRound.value = response.round || null
      myBids.value = response.bids || []
      maxBids.value = response.max_bids || 5
    }
  } catch (error) {
    console.error('加载竞标失败:', error)
  } finally {
    bidsLoading.value = false
  }
}

// 加载所有歌曲
const loadSongs = async () => {
  songsLoading.value = true
  try {
    const response = await getSongs({ page: 1, page_size: 1000 })
    if (response.success) {
      allSongs.value = response.results || []
      console.log('加载的歌曲列表:', allSongs.value)
      if (allSongs.value.length > 0) {
        console.log('第一首歌曲:', JSON.stringify(allSongs.value[0], null, 2))
        console.log('所有歌曲的网易云链接:', allSongs.value.map(s => ({ id: s.id, title: s.title, netease_url: s.netease_url })))
      }
    }
  } catch (error) {
    console.error('加载歌曲列表失败:', error)
    ElMessage.error('加载歌曲列表失败')
  } finally {
    songsLoading.value = false
  }
}

// 切换卡片展开状态
const toggleExpand = (songId) => {
  const index = expandedSongs.value.indexOf(songId)
  if (index > -1) {
    expandedSongs.value.splice(index, 1)
  } else {
    expandedSongs.value.push(songId)
  }
}

// 下载歌曲
const downloadSong = (song) => {
  if (!song.audio_url) {
    ElMessage.error('音频文件不可用')
    return
  }
  
  // 获取完整的音频 URL
  let audioUrl = song.audio_url
  if (!audioUrl.startsWith('http://') && !audioUrl.startsWith('https://')) {
    audioUrl = new URL(audioUrl, window.API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:8000`).href
  }
  
  console.log('下载音频:', audioUrl)
  
  // 使用 fetch 下载文件，这样可以改变文件名
  fetch(audioUrl)
    .then(response => {
      if (!response.ok) throw new Error('音频下载失败')
      return response.blob()
    })
    .then(blob => {
      // 创建下载链接
      const downloadUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = 'track.mp3'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(downloadUrl)
      ElMessage.success('音频下载成功')
    })
    .catch(error => {
      console.error('下载失败:', error)
      ElMessage.error('音频下载失败')
    })
}

// 打开网易云链接
const openNeteaseUrl = (url) => {
  if (url) {
    window.open(url, '_blank')
  }
}

// 显示竞标对话框
const showBidDialog = async (song) => {
  // 加载当前竞标轮次和用户信息
  try {
    // 获取竞标轮次（从 CompetitionPhase 获取）
    const roundsResponse = await getBiddingRounds()
    if (roundsResponse.success && roundsResponse.rounds.length > 0) {
      // 找活跃的竞标阶段
      const activeRound = roundsResponse.rounds.find(r => r.status === 'active')
      if (!activeRound) {
        ElMessage.warning('当前没有活跃的竞标轮次')
        return
      }
      currentRound.value = activeRound
      
      // 获取用户已有的竞标数
      const bidsResponse = await getMyBids(activeRound.id)
      if (bidsResponse.success) {
        myBidsCount.value = bidsResponse.bid_count || 0
        maxBids.value = bidsResponse.max_bids || 5
      }
    } else {
      ElMessage.warning('无法获取竞标信息')
      return
    }
    
    // 获取用户代币
    const profileResponse = await getUserProfile()
    if (profileResponse && profileResponse.token !== undefined) {
      userToken.value = profileResponse.token
    }
    
    // 设置竞标表单
    bidForm.value = {
      songId: song.id,
      songTitle: song.title,
      amount: null
    }
    bidDialogVisible.value = true
  } catch (error) {
    console.error('获取竞标信息失败:', error)
    ElMessage.error('无法打开竞标窗口')
  }
}

// 提交竞标
const handleSubmitBid = async () => {
  if (!bidForm.value.amount || bidForm.value.amount <= 0) {
    ElMessage.error('请输入有效的竞标金额')
    return
  }
  
  if (myBidsCount.value >= maxBids.value) {
    ElMessage.error(`已达到最大竞标数量限制（${maxBids.value}）`)
    return
  }
  
  if (userToken.value < bidForm.value.amount) {
    ElMessage.error(`代币余额不足（需要${bidForm.value.amount}，现有${userToken.value}）`)
    return
  }
  
  bidSubmitting.value = true
  try {
    const response = await submitBid({
      songId: bidForm.value.songId,
      amount: bidForm.value.amount,
      roundId: currentRound.value.id
    })
    
    if (response.success) {
      ElMessage.success('竞标已提交')
      bidDialogVisible.value = false
      // 刷新竞标列表
      await loadMyBids()
    }
  } catch (error) {
    console.error('竞标失败:', error)
    ElMessage.error(error.response?.data?.message || '竞标失败')
  } finally {
    bidSubmitting.value = false
  }
}

// 判断是否是自己的歌曲
const isMyOwnSong = (song) => {
  const username = localStorage.getItem('username')
  return username && song.user?.username === username
}

// 编辑歌曲
const editSong = (song) => {
  editForm.value = {
    id: song.id,
    title: song.title,
    netease_url: song.netease_url || ''
  }
  editDialogVisible.value = true
}

// 更新歌曲
const handleUpdateSong = async () => {
  updating.value = true
  try {
    console.log('发送更新请求:', {
      id: editForm.value.id,
      title: editForm.value.title,
      netease_url: editForm.value.netease_url
    })
    const response = await updateSong(editForm.value.id, {
      title: editForm.value.title,
      netease_url: editForm.value.netease_url
    })
    console.log('更新响应:', response)
    if (response.success) {
      ElMessage.success('更新成功')
      editDialogVisible.value = false
      await loadSongs()
      await loadMySongs()
    }
  } catch (error) {
    console.error('更新失败:', error)
    ElMessage.error('更新失败')
  } finally {
    updating.value = false
  }
}

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 获取竞标状态文本
const getBidStatusText = (status) => {
  const statusMap = {
    'bidding': '进行中',
    'won': '✓ 已中选',
    'lost': '已落选'
  }
  return statusMap[status] || '未知'
}

// 获取竞标状态标签类型
const getBidStatusType = (status) => {
  const typeMap = {
    'bidding': 'info',
    'won': 'success',
    'lost': 'danger'
  }
  return typeMap[status] || 'info'
}

// 获取完整的图片 URL
const getFullImageUrl = (url) => {
  if (!url) {
    console.log('图片 URL 为空')
    return null
  }
  
  // 如果已是完整 URL，直接返回
  if (url.startsWith('http://') || url.startsWith('https://')) {
    console.log('使用完整 URL:', url)
    return url
  }
  
  // 相对路径：获取 API 基础 URL 的主机部分
  // API 基础路径是 /api，所以媒体文件应该从相同的主机获取
  // 例如：相对路径 /media/songs/xxx.jpg 应该转换为 http://localhost:8000/media/songs/xxx.jpg
  try {
    // 方法 1：尝试从 API 调用的响应 URL 推断后端服务器
    // 通过发送一个简单的 OPTIONS 请求来获取完整的后端 URL
    const fullUrl = new URL(url, window.API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:8000`).href
    console.log('转换相对路径为:', fullUrl)
    return fullUrl
  } catch (e) {
    console.error('URL 转换失败:', e)
    return url
  }
}

// 图片加载错误处理
const handleImageError = (e) => {
  console.warn('图片加载失败:', {
    src: e.target.src,
    错误: e.target.error?.message || '未知错误'
  })
  e.target.style.display = 'none'
}

// 分页处理
const handlePageChange = (page) => {
  currentPage.value = page
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
}

// 滚动到歌曲列表
const scrollToSongs = () => {
  document.querySelector('.songs-list-card')?.scrollIntoView({ 
    behavior: 'smooth' 
  })
}

// 组件挂载时加载数据
onMounted(async () => {
  // 获取当前用户信息
  currentUser.value = {
    username: localStorage.getItem('username')
  }
  
  await Promise.all([
    loadMySongs(),
    loadMyBids(),
    loadSongs()
  ])
})
</script>

<style scoped>
.songs-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: bold;
}

.header-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
}

.upload-card,
.bids-card,
.songs-list-card {
  margin-bottom: 20px;
}

.title-hint {
  margin-top: 8px;
  display: flex;
  align-items: center;
}

.loading-container {
  padding: 20px;
}

.round-info {
  margin-bottom: 20px;
}

/* 歌曲网格布局 */
.songs-grid {
  display: grid;
  gap: 20px;
  margin-bottom: 20px;
}

.songs-grid.grid-small {
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 15px;
}

.songs-grid.grid-medium {
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.songs-grid.grid-list {
  grid-template-columns: 1fr;
  gap: 0;
}

.song-card {
  cursor: pointer;
}

.song-card.card-list {
  margin-bottom: 0;
  border-bottom: 1px solid #ebeef5;
}

.song-card.card-list:last-child {
  border-bottom: none;
}

.card-small,
.card-medium {
  transition: transform 0.2s;
}

.card-small:hover,
.card-medium:hover {
  transform: translateY(-5px);
}

.card-item {
  height: 100%;
}

/* 列表模式样式 */
.list-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 12px 15px;
  height: 50px;
}

.list-cover {
  flex-shrink: 0;
  width: 50px;
  height: 50px;
  border-radius: 4px;
  overflow: hidden;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  cursor: pointer;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.list-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder-small {
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  opacity: 0.8;
}

.list-info {
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.list-title {
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 4px;
}

.list-date {
  font-size: 12px;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 4px;
}

.list-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.list-actions .el-button {
  padding: 6px 12px;
}

/* 卡片模式样式 */
.song-cover {
  position: relative;
  width: 100%;
  padding-top: 100%;
  overflow: hidden;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  cursor: pointer;
}

.song-cover img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  opacity: 0.8;
}

.cover-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s;
  color: white;
}

.overlay-text {
  margin-top: 8px;
  font-size: 14px;
  font-weight: 500;
}

.song-cover:hover .cover-overlay {
  opacity: 1;
}

.song-title {
  padding: 15px;
  cursor: pointer;
}

.song-title h3 {
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: bold;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-small .song-title h3 {
  font-size: 14px;
}

.card-large .song-title h3 {
  font-size: 18px;
}

.song-meta {
  margin: 0;
  font-size: 12px;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 5px;
}

.card-small .song-meta {
  font-size: 11px;
}

.card-large .song-meta {
  font-size: 13px;
}

.meta-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.song-details {
  padding: 0 15px 15px;
}

.detail-item {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 15px;
}

.detail-actions .el-button {
  flex: 1;
  min-width: 100px;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

@media (max-width: 768px) {
  .songs-grid.grid-small {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 12px;
  }

  .songs-grid.grid-medium {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 15px;
  }

  .card-header {
    font-size: 16px;
  }

  .header-actions {
    flex-direction: column;
    align-items: flex-end;
  }

  .detail-actions .el-button {
    min-width: auto;
  }

  .list-item {
    padding: 10px 12px;
    gap: 12px;
  }

  .list-cover {
    width: 45px;
    height: 45px;
  }

  .list-title {
    font-size: 13px;
  }

  .list-date {
    font-size: 11px;
  }

  .list-actions .el-button {
    padding: 4px 8px;
    font-size: 12px;
  }
}
</style>
