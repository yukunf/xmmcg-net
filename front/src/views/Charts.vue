<template>
  <div class="charts-page">
    <el-container>
      <el-main>
        <!-- 1. 上传谱面组件 -->
        <el-card class="upload-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Upload /></el-icon>
              <span>上传谱面</span>
              <el-tag v-if="myBidResult" type="success" size="small">
                中标歌曲: {{ myBidResult.song.title }}
              </el-tag>
            </div>
          </template>

          <div v-if="!myBidResult && !resultLoading" class="no-result-hint">
            <el-empty description="您还没有中标歌曲，无法上传谱面" :image-size="120">
              <el-button type="primary" @click="$router.push('/songs')">前往竞标</el-button>
            </el-empty>
          </div>

          <div v-else-if="resultLoading" class="loading-container">
            <el-skeleton :rows="3" animated />
          </div>

          <el-form 
            v-else
            ref="uploadFormRef" 
            :model="uploadForm" 
            :rules="uploadRules" 
            label-width="100px"
            :disabled="uploading || !!myChart"
          >
            <el-alert 
              v-if="myChart" 
              title="您已上传过谱面，再次上传将覆盖旧文件" 
              type="warning" 
              :closable="false"
              class="mb-20"
            />

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
                    支持 JPG、PNG 格式，文件大小不超过 2MB
                  </div>
                </template>
              </el-upload>
            </el-form-item>

            <el-form-item label="谱面文件" prop="chartFile">
              <el-upload
                ref="chartUploadRef"
                :auto-upload="false"
                :limit="1"
                :on-change="handleChartChange"
                :on-remove="handleChartRemove"
                accept=".txt"
                :file-list="chartFileList"
              >
                <el-button :icon="Document">选择 maidata.txt</el-button>
                <template #tip>
                  <div class="el-upload__tip">
                    谱面文件必须命名为 <strong>maidata.txt</strong>，并包含 <strong>&des=谱师名</strong> 行
                  </div>
                </template>
              </el-upload>
            </el-form-item>

            <el-form-item label="谱师名义">
              <el-input 
                v-model="detectedDesigner" 
                placeholder="从 maidata.txt 自动解析"
                disabled
              />
              <div class="title-hint" v-if="detectedDesigner">
                <el-text type="success" size="small">✓ 已从谱面文件读取</el-text>
              </div>
            </el-form-item>

            <el-form-item>
              <el-button 
                type="primary" 
                @click="handleUpload"
                :loading="uploading"
              >
                {{ uploading ? '上传中...' : (myChart ? '覆盖上传' : '上传谱面') }}
              </el-button>
              <el-button @click="resetUploadForm">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 2. 谱面列表 -->
        <el-card class="charts-list-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><List /></el-icon>
              <span>谱面列表</span>
              <div class="header-actions">
                <el-button 
                  type="primary" 
                  :icon="Refresh" 
                  @click="loadCharts"
                  circle
                />
              </div>
            </div>
          </template>

          <div v-if="chartsLoading" class="loading-container">
            <el-skeleton :rows="5" animated />
          </div>

          <el-empty 
            v-else-if="charts.length === 0" 
            description="暂无谱面"
            :image-size="200"
          />

          <div v-else class="charts-grid">
            <el-card
              v-for="chart in charts"
              :key="chart.id"
              class="chart-card"
              shadow="hover"
            >
              <!-- 封面 -->
              <div class="chart-cover" @click="viewCover(chart)">
                <img 
                  v-if="chart.cover_url" 
                  :src="chart.cover_url" 
                  :alt="chart.song.title"
                />
                <div v-else class="cover-placeholder">
                  <el-icon :size="60"><Document /></el-icon>
                </div>
              </div>

              <!-- 信息 -->
              <div class="chart-info">
                <h3 class="chart-title">{{ chart.song.title }}</h3>
                
                <div class="chart-meta">
                  <el-tag :type="getStatusType(chart.status)" size="small">
                    {{ chart.status_display }}
                  </el-tag>
                  <span class="designer">{{ chart.designer }}</span>
                </div>


                <div class="chart-time">
                  <el-icon size="12"><Clock /></el-icon>
                  {{ formatDate(chart.created_at) }}
                </div>
              </div>

              <!-- 操作按钮 -->
              <div class="chart-actions">
                <el-button
                  type="primary"
                  size="small"
                  :icon="Download"
                  @click="downloadZip(chart)"
                >
                  下载谱面
                </el-button>
              </div>
            </el-card>
          </div>

          <!-- 分页 -->
          <el-pagination
            v-if="totalCharts > pageSize"
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="totalCharts"
            layout="total, sizes, prev, pager, next, jumper"
            class="pagination"
            @current-change="handlePageChange"
            @size-change="handleSizeChange"
          />
        </el-card>
      </el-main>
    </el-container>

    <!-- 封面预览对话框 -->
    <el-dialog v-model="coverDialogVisible" title="封面预览" width="600px">
      <img :src="currentCover" style="width: 100%;" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Picture, Document, List, Refresh, Download, Clock } from '@element-plus/icons-vue'
import JSZip from 'jszip'
import { saveAs } from 'file-saver'
import { getBidResults, getCharts, getMyCharts, submitChart } from '../api'

// ==================== 数据 ====================
const uploading = ref(false)
const resultLoading = ref(true)
const chartsLoading = ref(false)

const myBidResult = ref(null)
const myChart = ref(null)

const uploadFormRef = ref(null)
const uploadForm = reactive({
  audioFile: null,
  coverImage: null,
  chartFile: null
})

const audioFileList = ref([])
const coverFileList = ref([])
const chartFileList = ref([])
const detectedDesigner = ref('')

const charts = ref([])
const totalCharts = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const coverDialogVisible = ref(false)
const currentCover = ref('')

// ==================== 表单验证 ====================
const uploadRules = {
  audioFile: [{ required: true, message: '请选择音频文件', trigger: 'change' }],
  coverImage: [{ required: true, message: '请选择封面图片', trigger: 'change' }],
  chartFile: [
    { required: true, message: '请选择谱面文件', trigger: 'change' },
    {
      validator: (rule, value, callback) => {
        if (!detectedDesigner.value) {
          callback(new Error('请填写谱师名义'))
        } else {
          callback()
        }
      },
      trigger: 'change'
    }
  ]
}

// ==================== 文件上传处理 ====================
const handleAudioChange = (file) => {
  uploadForm.audioFile = file.raw
  audioFileList.value = [file]
}

const handleAudioRemove = () => {
  uploadForm.audioFile = null
  audioFileList.value = []
}

const handleCoverChange = (file) => {
  uploadForm.coverImage = file.raw
  coverFileList.value = [file]
}

const handleCoverRemove = () => {
  uploadForm.coverImage = null
  coverFileList.value = []
}

const handleChartChange = async (file) => {
  uploadForm.chartFile = file.raw
  chartFileList.value = [file]
  
  // 读取文件并解析 &des= 行
  try {
    const text = await file.raw.text()
    const match = text.match(/^\s*&des=(.+)$/m)
    if (match && match[1].trim()) {
      detectedDesigner.value = match[1].trim()
      ElMessage.success(`已读取谱师名义: ${detectedDesigner.value}`)
    } else {
      detectedDesigner.value = ''
      ElMessage.error('请在 maidata.txt 中填写 &des=谱师名')
    }
  } catch (error) {
    ElMessage.error('读取谱面文件失败')
    detectedDesigner.value = ''
  }
}

const handleChartRemove = () => {
  uploadForm.chartFile = null
  chartFileList.value = []
  detectedDesigner.value = ''
}

const resetUploadForm = () => {
  uploadForm.audioFile = null
  uploadForm.coverImage = null
  uploadForm.chartFile = null
  audioFileList.value = []
  coverFileList.value = []
  chartFileList.value = []
  detectedDesigner.value = ''
  uploadFormRef.value?.resetFields()
}

// ==================== 上传谱面 ====================
const handleUpload = async () => {
  if (!uploadFormRef.value) return
  
  await uploadFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    if (!detectedDesigner.value) {
      ElMessage.error('请填写谱师名义')
      return
    }
    
    uploading.value = true
    
    const formData = new FormData()
    formData.append('audio_file', uploadForm.audioFile)
    formData.append('cover_image', uploadForm.coverImage)
    formData.append('chart_file', uploadForm.chartFile)
    
    try {
      const res = await submitChart(myBidResult.value.id, formData)
      if (res.success) {
        ElMessage.success(res.message || '谱面上传成功')
        resetUploadForm()
        await loadMyBidResult()
        await loadCharts()
      } else {
        ElMessage.error(res.message || '上传失败')
      }
    } catch (error) {
      console.error('上传谱面失败:', error)
      const msg = error.response?.data?.errors?.chart_file?.[0] || error.response?.data?.message || '上传失败'
      ElMessage.error(msg)
    } finally {
      uploading.value = false
    }
  })
}

// ==================== 加载数据 ====================
const loadMyBidResult = async () => {
  resultLoading.value = true
  try {
    const res = await getBidResults()
    
    if (res.success && res.results && res.results.length > 0) {
      // 取第一个歌曲类型的中标结果
      myBidResult.value = res.results.find(r => r.bid_type === 'song')
      
      // 检查是否已有谱面
      if (myBidResult.value) {
        const chartRes = await getMyCharts()
        
        if (chartRes.success && chartRes.charts) {
          myChart.value = chartRes.charts.find(c => c.song.id === myBidResult.value.song.id)
        }
      }
    }
  } catch (error) {
    console.error('加载中标结果失败:', error)
  } finally {
    resultLoading.value = false
  }
}

const loadCharts = async () => {
  chartsLoading.value = true
  try {
    const res = await getCharts({
      page: currentPage.value,
      page_size: pageSize.value
    })
    if (res.success) {
      charts.value = res.results || []
      totalCharts.value = res.count || 0
    }
  } catch (error) {
    console.error('加载谱面列表失败:', error)
    ElMessage.error('加载谱面列表失败')
  } finally {
    chartsLoading.value = false
  }
}

const handlePageChange = () => {
  loadCharts()
}

const handleSizeChange = () => {
  currentPage.value = 1
  loadCharts()
}

// ==================== 工具函数 ====================
const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getStatusType = (status) => {
  const types = {
    'part_submitted': 'warning',
    'final_submitted': 'success',
    'under_review': 'info',
    'reviewed': 'primary',
    'created': 'info'  // 兼容旧状态
  }
  return types[status] || 'info'
}



const sanitizeFilename = (name) => {
  return name.replace(/[\\/:*?"<>|]/g, '_').trim() || 'chart'
}

const getExtFromUrl = (url, fallback) => {
  try {
    const pathname = new URL(url).pathname
    const idx = pathname.lastIndexOf('.')
    if (idx !== -1) return pathname.substring(idx + 1).toLowerCase()
  } catch (e) {}
  return fallback
}

const fetchAsArrayBuffer = async (url) => {
  const res = await fetch(url, { credentials: 'include' })
  if (!res.ok) throw new Error(`获取失败: ${url}`)
  return await res.arrayBuffer()
}

const downloadZip = async (chart) => {
  const zip = new JSZip()
  const folderName = sanitizeFilename(chart.song.title)

  const tasks = []

  if (chart.chart_file_url) {
    tasks.push(
      (async () => {
        const buf = await fetchAsArrayBuffer(chart.chart_file_url)
        zip.file(`${folderName}/maidata.txt`, buf)
      })()
    )
  }

  if (chart.audio_url) {
    tasks.push(
      (async () => {
        const buf = await fetchAsArrayBuffer(chart.audio_url)
        const ext = getExtFromUrl(chart.audio_url, 'mp3')
        zip.file(`${folderName}/audio.${ext}`, buf)
      })()
    )
  }

  if (chart.cover_url) {
    tasks.push(
      (async () => {
        const buf = await fetchAsArrayBuffer(chart.cover_url)
        const ext = getExtFromUrl(chart.cover_url, 'jpg')
        zip.file(`${folderName}/cover.${ext}`, buf)
      })()
    )
  }

  if (tasks.length === 0) {
    ElMessage.error('没有可下载的文件')
    return
  }

  try {
    ElMessage.info('正在打包下载...')
    await Promise.all(tasks)
    const content = await zip.generateAsync({ type: 'blob' })
    saveAs(content, `${folderName}.zip`)
  } catch (e) {
    console.error(e)
    ElMessage.error('打包失败，请稍后重试')
  }
}
const viewCover = (chart) => {
  if (chart.cover_url) {
    currentCover.value = chart.cover_url
    coverDialogVisible.value = true
  } else {
    ElMessage.error('封面不存在')
  }
}

// ==================== 生命周期 ====================
onMounted(async () => {
  await loadMyBidResult()
  await loadCharts()
})
</script>

<style scoped>
.charts-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: bold;
}

.header-actions {
  margin-left: auto;
  display: flex;
  gap: 10px;
}

.upload-card,
.charts-list-card {
  margin-bottom: 20px;
}

.no-result-hint {
  padding: 40px 0;
}

.loading-container {
  padding: 20px;
}

.mb-20 {
  margin-bottom: 20px;
}

.title-hint {
  margin-top: 5px;
}

.pagination {
  margin-top: 20px;
  justify-content: center;
}
.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.chart-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chart-cover {
  width: 100%;
  height: 200px;
  overflow: hidden;
  cursor: pointer;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chart-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.chart-cover:hover img {
  transform: scale(1.05);
}

.cover-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: #909399;
}

.chart-info {
  padding: 15px;
  flex: 1;
}

.chart-title {
  font-size: 16px;
  font-weight: bold;
  margin: 0 0 10px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chart-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.designer {
  font-size: 14px;
  color: #606266;
}


.chart-time {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #909399;
}

.chart-actions {
  padding: 0 15px 15px;
  display: flex;
  gap: 10px;
}

.chart-actions .el-button {
  flex: 1;
}

@media (max-width: 768px) {
  .charts-page {
    padding: 10px;
  }
  
  .charts-grid {
    grid-template-columns: 1fr;
    padding: 10px;
  }
}
</style>
