<template>
  <div class="charts-page">
    <el-container>
      <el-main>
        <el-card class="upload-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Upload /></el-icon>
              <span>{{ uploadCardTitle }}</span>
              
              <el-tag v-if="myBidResult" type="success" size="small" style="margin-right: 5px;">
                中标歌曲: {{ getBidResultSongTitle(myBidResult) }}
              </el-tag>
              
              <el-tag v-if="myBidResult && isSecondStage" type="warning" size="small" style="margin-right: 5px;">
                二次竞标
              </el-tag>

              <el-tag v-if="designerQQ" type="info" size="small" effect="plain">
                谱师QQ: {{ designerQQ }}
              </el-tag>

            </div>
          </template>

          <!-- 阶段外禁用提示 -->
          <el-alert
            v-if="!isChartingPhase && !resultLoading"
            title="上传已关闭"
            type="warning"
            :closable="false"
            show-icon
            class="mb-20"
          >
            <template #default>
              上传谱面功能仅在 <strong>制谱期</strong> 开放。当前阶段：<strong>{{ currentPhaseName }}</strong>
            </template>
          </el-alert>

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
            :disabled="uploading || !isChartingPhase || !!myChart"
          >
            <el-alert 
              v-if="stageDescription" 
              :title="stageDescription" 
              :type="isSecondStage ? 'success' : 'info'" 
              :closable="false"
              class="mb-20"
              show-icon
            />
            
            <el-alert 
              v-if="myChart" 
              :title="isSecondStage ? '您已提交第二阶段完成稿，无法再次上传' : '您已提交第一阶段半成品，请等待第二阶段竞标'" 
              type="warning" 
              :closable="false"
              class="mb-20"
              show-icon
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

            <el-form-item label="背景视频" prop="backgroundVideo">
              <el-upload
                ref="videoUploadRef"
                :auto-upload="false"
                :limit="1"
                :on-change="handleVideoChange"
                :on-remove="handleVideoRemove"
                accept=".mp4"
                :file-list="videoFileList"
              >
                <el-button :icon="VideoCamera">选择视频（可选）</el-button>
                <template #tip>
                  <div class="el-upload__tip">
                    支持 MP4 格式，文件名需以 bg 或 pv 开头（如: bg.mp4, pv.mp4），文件大小不超过 20MB
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
                :disabled="!!myChart"
              >
                {{ uploadButtonText }}
              </el-button>
              <el-button @click="resetUploadForm">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
        <!-- TODO 校验只有完成了前半的谱师才能竞标，还是放开？现在是放开的没有校验，还是加上吧之后。-->
        <!-- 2. 我的谱面竞标组件 -->
        <el-card class="my-bids-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><TrophyBase /></el-icon>
              <span>我的谱面竞标</span>
              <el-button 
                size="small" 
                type="primary" 
                :icon="Refresh" 
                @click="loadMyChartBids"
                circle
              />
            </div>
          </template>

          <div v-if="chartBidsLoading" class="loading-container">
            <el-skeleton :rows="3" animated />
          </div>

          <el-empty 
            v-else-if="!currentChartBidRound" 
            description="当前没有活跃的谱面竞标轮次"
            :image-size="120"
          />

          <div v-else>
            <el-alert 
              :title="`当前轮次：${currentChartBidRound.name}`" 
              type="info" 
              :closable="false"
              class="round-info"
            >
              <template #default>
                已竞标 {{ myChartBids.length }}/{{ maxChartBids }} 份
              </template>
            </el-alert>

            <el-empty 
              v-if="myChartBids.length === 0" 
              description="您还没有竞标任何谱面"
              :image-size="120"
            >
              <el-button type="primary" @click="scrollToCharts">去浏览谱面</el-button>
            </el-empty>

            <el-table v-else :data="myChartBids" stripe style="width: 100%">
              <el-table-column label="歌曲标题" min-width="200">
                <template #default="{ row }">
                  {{ row.chart?.song?.title || '未知歌曲' }}
                </template>
              </el-table-column>
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
              <el-table-column label="操作" width="150" align="center">
                <template #default="{ row }">
                  <el-button
                    v-if="row.status === 'won'"
                    type="success"
                    size="small"
                    :icon="Download"
                    @click="downloadChart(row.chart)"
                  >
                    下载
                  </el-button>
                  <el-button
                    v-if="row.status === 'bidding'"
                    type="danger"
                    size="small"
                    @click="handleWithdrawBid(row)"
                  >
                    撤回
                  </el-button>
                  <span v-else-if="row.status !== 'won'" style="color: #ccc; font-size: 12px;">-</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>

        <!-- 3. 谱面列表 -->
        <el-card class="charts-list-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><List /></el-icon>
              <span>谱面列表</span>
              <div class="header-actions">
                <el-select 
                  v-model="selectedStatusFilter" 
                  placeholder="状态筛选"
                  clearable
                  style="width: 140px; margin-right: 10px;"
                >
                  <el-option label="半成品" value="part_submitted" />
                  <el-option label="完成稿" value="final_submitted" />
                </el-select>
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
              v-for="chart in filteredCharts"
              :key="chart.id"
              class="chart-card"
              shadow="hover"
            >
              <div class="chart-cover" @click="toggleExpand(chart.id)" title="点击展开/收起详情">
                <img 
                  v-if="chart.cover_url" 
                  :src="chart.cover_url" 
                  :alt="chart.song.title"
                />
                <div v-else class="cover-placeholder">
                  <el-icon :size="60"><Document /></el-icon>
                </div>
                <div class="cover-overlay" v-if="!expandedCharts.includes(chart.id)">
                    <el-icon><CaretBottom /></el-icon>
                </div>
              </div>

              <div class="chart-info">
                <h3 class="chart-title" @click="toggleExpand(chart.id)" style="cursor: pointer;">
                    {{ getChartDisplayTitle(chart) }}
                </h3>
                
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

              <el-collapse-transition>
                <div v-show="expandedCharts.includes(chart.id)" class="chart-details-expand">
                  <div class="bids-section">
                    <div class="section-title">
                      <span>当前竞标行情</span>
                      <el-tag v-if="chartBidsMap[chart.id]?.count" size="small" type="info" round>
                        {{ chartBidsMap[chart.id]?.count }} 人出价
                      </el-tag>
                      <el-button 
                        link 
                        type="primary" 
                        size="small" 
                        :icon="Refresh"
                        :loading="chartBidsMap[chart.id]?.loading"
                        @click="fetchChartBids(chart.id)"
                        style="margin-left: auto;"
                      >
                        刷新
                      </el-button>
                    </div>

                    <el-skeleton v-if="chartBidsMap[chart.id]?.loading && !chartBidsMap[chart.id]?.list.length" :rows="2" animated />

                    <div v-else-if="!chartBidsMap[chart.id]?.list || chartBidsMap[chart.id]?.list.length === 0" class="no-bids">
                      <el-text type="info" size="small">暂无竞标记录</el-text>
                    </div>

                    <el-table 
                      v-else 
                      :data="chartBidsMap[chart.id]?.list" 
                      size="small" 
                      style="width: 100%;"
                      max-height="200"
                      :row-class-name="({ row }) => row.is_self ? 'my-bid-row' : ''"
                    >
                      <el-table-column prop="username" label="用户">
                        <template #default="{ row }">
                          <span v-if="row.is_self" class="highlight-self">(我) #{{ row.username }}</span>
                          <span v-else style="font-weight: regular;">#{{ row.username }}</span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="amount" label="出价" width="80">
                        <template #default="{ row }">
                          <span class="highlight-price">{{ row.amount }}</span>
                        </template>
                      </el-table-column>
                      <el-table-column prop="created_at" label="时间" width="110">
                        <template #default="{ row }">
                          <span class="time-text">{{ formatDate(row.created_at).split(' ')[0] }}</span>
                        </template>
                      </el-table-column>
                    </el-table>
                  </div>
                  
                  <div style="text-align: center; margin-bottom: 10px;">
                    <el-button link type="info" size="small" @click="viewCover(chart)">查看封面大图</el-button>
                  </div>
                </div>
              </el-collapse-transition>

              <div class="chart-actions">
                <el-button
                  type="primary"
                  size="small"
                  :icon="Download"
                  @click="downloadZip(chart)"
                >
                  下载
                </el-button>
                <el-button
                  v-if="chart.is_part_one && chart.status === 'part_submitted'"
                  type="success"
                  size="small"
                  :icon="TrophyBase"
                  @click="showChartBidDialog(chart)"
                >
                  竞标
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

    <!-- 谱面竞标对话框 -->
    <el-dialog
      v-model="chartBidDialogVisible"
      title="竞标谱面"
      width="450px"
    >
      <el-form
        :model="chartBidForm"
        label-width="80px"
      >
        <el-form-item label="谱面">
          <el-text>{{ chartBidForm.chartTitle }}</el-text>
        </el-form-item>
        
        <el-form-item label="谱师">
          <el-text>{{ chartBidForm.designer }}</el-text>
        </el-form-item>
        
        <el-form-item label="竞标轮次">
          <el-text v-if="currentChartBidRound">
            {{ currentChartBidRound.name }}
          </el-text>
        </el-form-item>
        
        <el-divider />
        
        <el-form-item label="代币余额">
          <el-tag type="info">{{ userChartBidToken }} 代币</el-tag>
        </el-form-item>
        
        <el-form-item label="已竞标">
          <el-text>
            {{ myChartBidsCount }} / {{ maxChartBids }}
          </el-text>
        </el-form-item>
        
        <el-divider />
        
        <el-form-item label="出价" prop="amount">
          <el-input-number
            v-model="chartBidForm.amount"
            :min="1"
            placeholder="输入竞标金额"
            style="width: 100%"
          />
        </el-form-item>
        
        <el-alert
          v-if="chartBidForm.amount && chartBidForm.amount > userChartBidToken"
          title="代币不足"
          type="error"
          :closable="false"
          style="margin-bottom: 10px"
        />
        
        <el-alert
          v-if="myChartBidsCount >= maxChartBids"
          title="已达到竞标数量限制"
          type="warning"
          :closable="false"
          style="margin-bottom: 10px"
        />
      </el-form>
      
      <template #footer>
        <el-button @click="chartBidDialogVisible = false">取消</el-button>
        <el-button 
          type="success" 
          @click="handleSubmitChartBid" 
          :loading="chartBidSubmitting"
          :disabled="!chartBidForm.amount || chartBidForm.amount > userChartBidToken || myChartBidsCount >= maxChartBids"
        >
          提交竞标
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Picture, VideoCamera, Document, List, Refresh, Download, Clock, TrophyBase, CaretBottom } from '@element-plus/icons-vue'
import JSZip from 'jszip'
import { saveAs } from 'file-saver'
import { getBidResults, getCharts, getMyCharts, submitChart, getCurrentPhase, getMyBids, getBiddingRounds, submitBid, 
  getUserProfile, deleteBid, getUserPublicInfo, getTargetBids, downloadChartBundle } from '../api'

// ==================== 数据 ====================
const uploading = ref(false)
const resultLoading = ref(true)
const chartsLoading = ref(false)
const chartBidsLoading = ref(false)

const myBidResult = ref(null)
const myChart = ref(null)

// 阶段相关
const currentPhase = ref(null)
const isChartingPhase = ref(false)
const currentPhaseName = ref('')

const uploadFormRef = ref(null)
const uploadForm = reactive({
  audioFile: null,
  coverImage: null,
  backgroundVideo: null,
  chartFile: null
})

const audioFileList = ref([])
const coverFileList = ref([])
const videoFileList = ref([])
const chartFileList = ref([])
const detectedDesigner = ref('')
const videoUploadRef = ref(null)

const charts = ref([])
const totalCharts = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const coverDialogVisible = ref(false)
const currentCover = ref('')

// 谱面竞标相关
const expandedCharts = ref([]) // 存储已展开的 chartId
const chartBidsMap = ref({})   // 存储每个 chartId 对应的竞标数据 { loading, list, count }

const currentChartBidRound = ref(null)
const myChartBids = ref([])
const maxChartBids = ref(5)
const selectedStatusFilter = ref('')

// 竞标对话框
const chartBidDialogVisible = ref(false)
const chartBidForm = reactive({
  chartId: null,
  chartTitle: '',
  designer: '',
  amount: null
})
const chartBidSubmitting = ref(false)
const userChartBidToken = ref(0)
const myChartBidsCount = ref(0)

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

// 计算属性：筛选后的谱面列表
const filteredCharts = computed(() => {
  if (!selectedStatusFilter.value) {
    return charts.value
  }
  return charts.value.filter(chart => chart.status === selectedStatusFilter.value)
})

// 计算属性：判断是否为第二阶段（谱面竞标）
const isSecondStage = computed(() => {
  return myBidResult.value?.bid_type === 'chart'
})

// 计算属性：上传卡片标题
const uploadCardTitle = computed(() => {
  if (!myBidResult.value) return '上传谱面'
  return isSecondStage.value ? '上传谱面（完成稿）' : '上传谱面（半成品）'
})

// 计算属性：阶段说明
const stageDescription = computed(() => {
  if (!myBidResult.value) return ''
  if (isSecondStage.value) {
    return '📝 第二阶段：您中标了谱面竞标，请继续完成该谱面并提交完成稿'
  }
  return '📝 第一阶段：您中标了歌曲竞标，请制作半成品谱面并上传'
})

// 计算属性：上传按钮文本
const uploadButtonText = computed(() => {
  if (uploading.value) return '上传中...'
  if (myChart.value) return '已提交'
  return isSecondStage.value ? '提交完成稿' : '提交半成品'
})

// 获取谱面显示标题（处理重复标题）
const getChartDisplayTitle = (chart) => {
  if (!chart || !chart.song || !chart.song.title) {
    return 'Unknown'
  }
  
  const title = String(chart.song.title).trim()
  const designer = chart.designer || 'Unknown'
  
  // 计算相同标题的谱面数量（基于所有谱面，不受筛选影响）
  const sameTitle = charts.value.filter(c => {
    return c.song && c.song.title && String(c.song.title).trim() === title
  })
  
  // 如果有重复标题，添加[谱师名称]后缀
  if (sameTitle.length > 1) {
    return `${title} [${designer}]`
  }
  
  return title
}



// ==================== 获取竞标QQ ====================
// 假设 myBidResult 是你的数据源（可能是 props 传进来的，也可能是当前页面 fetch 到的 ref）
// 这里假设它是当前页面的一个 ref 或者是 props
// const props = defineProps({ myBidResult: Object }) // 如果是子组件用这个


// ✅ 2. 定义一个变量专门存 QQ
const designerQQ = ref('')

// ✅ 3. 核心逻辑：监听 myBidResult 变动
// 当 myBidResult 有值了，说明中标结果出来了，我们立刻拿着 ID 去查 QQ
// ✅ 3. 修正后的逻辑：去 chart 对象里找 user_id
watch(
  () => myBidResult.value,
  async (newResult) => {
    designerQQ.value = '' // 重置
    
    if (!newResult) return

    // 1. 只有谱面竞标 (Stage 2) 才需要显示原作者 QQ
    if (newResult.bid_type === 'chart' && newResult.chart?.user_id) {
      try {
        const res = await getUserPublicInfo(newResult.chart.user_id)
        
        // 💡 修正点：你的 axios 返回了完整对象，数据在 res.data 里
        // 我们兼容两种情况（有data解包和没data解包）
        const serverData = res.data || res 
        
        if (serverData && serverData.qqid) {
            designerQQ.value = serverData.qqid
        }
      } catch (error) {
        console.error('获取谱师QQ失败', error)
      }
    }
  },
  { immediate: true }
)



// 切换卡片展开状态
const toggleExpand = async (chartId) => {
  const index = expandedCharts.value.indexOf(chartId)
  
  if (index > -1) {
    // 收起
    expandedCharts.value.splice(index, 1)
  } else {
    // 展开
    expandedCharts.value.push(chartId)
    // 获取数据
    await fetchChartBids(chartId)
  }
}

// 获取单张谱面的竞标数据
const fetchChartBids = async (chartId) => {
  // 初始化数据结构
  if (!chartBidsMap.value[chartId]) {
    chartBidsMap.value[chartId] = { loading: true, list: [], count: 0 }
  } else {
    chartBidsMap.value[chartId].loading = true
  }
  
  try {
    const params = { chart_id: chartId }

    // 如果前端已知当前的谱面竞标轮次，带上 round_id
    if (currentChartBidRound.value && currentChartBidRound.value.id) {
        params.round_id = currentChartBidRound.value.id
    }
    
    const res = await getTargetBids(params)

    if (res.success) {
      chartBidsMap.value[chartId].list = res.results || []
      chartBidsMap.value[chartId].count = res.count || 0
    } else {
      chartBidsMap.value[chartId].list = []
      chartBidsMap.value[chartId].count = 0
    }
  } catch (error) {
    console.error(`获取谱面 ${chartId} 竞标行情失败`, error)
    chartBidsMap.value[chartId].list = []
  } finally {
    if (chartBidsMap.value[chartId]) {
      chartBidsMap.value[chartId].loading = false
    }
  }
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

const handleVideoChange = (file) => {
  // 验证文件大小（20MB）
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.error('背景视频大小不能超过 20MB')
    videoFileList.value = []
    uploadForm.backgroundVideo = null
    return
  }
  // 验证文件格式
  const ext = file.name.split('.').pop().toLowerCase()
  if (ext !== 'mp4') {
    ElMessage.error('仅支持 MP4 格式')
    videoFileList.value = []
    uploadForm.backgroundVideo = null
    return
  }
  // 验证文件名
  const filename = file.name.toLowerCase()
  if (!filename.startsWith('bg.') && !filename.startsWith('pv.')) {
    ElMessage.error('视频文件名必须以 bg 或 pv 开头（如: bg.mp4, pv.mp4）')
    videoFileList.value = []
    uploadForm.backgroundVideo = null
    return
  }
  uploadForm.backgroundVideo = file.raw
  videoFileList.value = [file]
}

const handleVideoRemove = () => {
  uploadForm.backgroundVideo = null
  videoFileList.value = []
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
  uploadForm.backgroundVideo = null
  uploadForm.chartFile = null
  audioFileList.value = []
  coverFileList.value = []
  videoFileList.value = []
  chartFileList.value = []
  detectedDesigner.value = ''
  uploadFormRef.value?.resetFields()
}

// 构造可用的完整 URL（兼容相对路径）
const resolveUrl = (url) => {
  if (!url) return null
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  try {
    return new URL(url, window.API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:8000`).href
  } catch (e) {
    console.error('URL 转换失败:', e)
    return url
  }
}

// ==================== 上传谱面 ====================
const handleUpload = async () => {
  console.log('=== handleUpload 开始 ===')
  console.log('myBidResult.value:', myBidResult.value)
  console.log('uploading.value:', uploading.value)
  
  // 检查是否中标
  if (!myBidResult.value) {
    console.error('错误：还没有中标，无法上传谱面')
    ElMessage.error('还没有中标，无法上传谱面')
    return
  }
  
  console.log('✓ 已中标，继续...')
  
  if (!uploadFormRef.value) {
    console.error('错误：uploadFormRef 不存在')
    return
  }
  
  console.log('✓ uploadFormRef 存在，开始验证表单...')
  
  await uploadFormRef.value.validate(async (valid) => {
    console.log('表单验证结果:', valid)
    
    if (!valid) {
      console.error('表单验证失败')
      return
    }
    
    console.log('✓ 表单验证通过')
    console.log('detectedDesigner.value:', detectedDesigner.value)
    
    if (!detectedDesigner.value) {
      console.error('错误：没有检测到谱师名义')
      ElMessage.error('请填写谱师名义')
      return
    }
    
    console.log('✓ 谱师名义已检测')
    
    // 确定上传类型
    const isSecondStageUpload = myBidResult.value.bid_type === 'chart'
    const uploadType = isSecondStageUpload ? '完成稿' : '半成品'
    const songTitle = myBidResult.value.song?.title || '未知歌曲'
    
    console.log('上传信息:', {
      isSecondStageUpload,
      uploadType,
      songTitle,
      bid_type: myBidResult.value.bid_type,
      bidResultId: myBidResult.value.id
    })
    
    // 显示上传确认对话框
    console.log('显示上传确认对话框...')
    ElMessageBox.confirm(
      `<div style="text-align: left; line-height: 1.8;">
        <p><strong>谱面标题：</strong>${songTitle}</p>
        <p><strong>上传类型：</strong><span style="color: ${isSecondStageUpload ? '#E6A23C' : '#409EFF'}">${uploadType}</span></p>
        <p><strong>谱师名义：</strong>${detectedDesigner.value}</p>
        <p style="margin-top: 12px; color: #606266; font-size: 12px;">
          ${isSecondStageUpload ? '⚠️ 您正在提交该谱面的<strong>完成稿</strong>，此后该谱面将进入互评阶段。' : 'ℹ️ 您正在提交该谱面的<strong>半成品</strong>，可以继续编辑并在第二阶段提交完成稿。'}
        </p>
      </div>`,
      '确认上传谱面',
      {
        confirmButtonText: '确认上传',
        cancelButtonText: '取消',
        type: 'info',
        dangerouslyUseHTMLString: true,
        center: true
      }
    ).then(async () => {
      console.log('✓ 用户点击了"确认上传"')
      uploading.value = true
      
      const formData = new FormData()
      console.log('附加文件到 FormData:')
      
      if (uploadForm.audioFile) {
        formData.append('audio_file', uploadForm.audioFile)
        console.log('  ✓ audio_file:', uploadForm.audioFile.name)
      } else {
        console.error('  ✗ 缺少 audio_file')
      }
      
      if (uploadForm.coverImage) {
        formData.append('cover_image', uploadForm.coverImage)
        console.log('  ✓ cover_image:', uploadForm.coverImage.name)
      } else {
        console.error('  ✗ 缺少 cover_image')
      }
      
      if (uploadForm.backgroundVideo) {
        formData.append('background_video', uploadForm.backgroundVideo)
        console.log('  ✓ background_video:', uploadForm.backgroundVideo.name)
      } else {
        console.log('  - background_video: 可选，未提供')
      }
      
      if (uploadForm.chartFile) {
        formData.append('chart_file', uploadForm.chartFile)
        console.log('  ✓ chart_file:', uploadForm.chartFile.name)
      } else {
        console.error('  ✗ 缺少 chart_file')
      }
      
      console.log('调用 submitChart API，resultId:', myBidResult.value.id)
      
      try {
        const res = await submitChart(myBidResult.value.id, formData)
        console.log('API 响应:', res)
        
        if (res.success) {
          console.log('✓ 上传成功')
          ElMessage.success({
            message: `✓ 成功上传${uploadType}谱面：${songTitle}`,
            type: 'success',
            duration: 3000
          })
          resetUploadForm()
          await loadMyBidResult()
          await loadCharts()
        } else {
          console.error('API 返回失败:', res.message)
          ElMessage.error(res.message || '上传失败')
        }
      } catch (error) {
        console.error('上传谱面异常:', error)
        console.error('错误响应:', error.response?.data)
        const msg = error.response?.data?.errors?.chart_file?.[0] || error.response?.data?.message || '上传失败'
        ElMessage.error(msg)
      } finally {
        uploading.value = false
        console.log('=== handleUpload 结束 ===')
      }
    }).catch(() => {
      console.log('用户点击了"取消"')
      ElMessage.info('已取消上传')
    })
  })
}

// ==================== 下载谱面包（音频+封面+视频+谱面） ====================
const downloadZip = async (chart) => {
  try {
    ElMessage.info('正在准备下载谱面包，请稍候...')

    // 优先使用后端打包直链下载（新窗口不会受 XHR/CORS 限制）
    try {
      const bundleUrl = `${window.API_BASE_URL || (window.location.protocol + '//' + window.location.hostname + ':8000')}/api/songs/charts/${chart.id}/bundle/`
      const win = window.open(bundleUrl, '_blank')
      if (win) {
        ElMessage.success('已在新窗口开始下载谱面包')
        return
      }
    } catch (serverBundleErr) {
      console.warn('后端打包直链下载失败，回退到前端打包：', serverBundleErr)
    }

    const zip = new JSZip()

    const fetchAndAdd = async (url, filename) => {
      if (!url) return
      const fullUrl = resolveUrl(url)
      try {
        const res = await fetch(fullUrl, {
          credentials: 'include',
          mode: 'cors',
          cache: 'no-store'
        })
        if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`)
        const blob = await res.blob()
        zip.file(filename, blob)
      } catch (e) {
        console.error('资源下载失败:', { filename, fullUrl, error: e })
        throw e
      }
    }

    // 音频
    await fetchAndAdd(chart.audio_url, 'track.mp3')

    // 封面
    if (chart.cover_url) {
      const ext = chart.cover_url.split('.').pop().split('?')[0]
      await fetchAndAdd(chart.cover_url, `bg.${ext}`)
    }

    // 视频（可选，失败不阻塞整体下载）
    if (chart.video_url) {
      const videoName = chart.video_url.includes('bg') ? 'bg.mp4' : 'pv.mp4'
      const fullUrl = resolveUrl(chart.video_url)
      try {
        const res = await fetch(fullUrl, {
          credentials: 'include',
          mode: 'cors',
          cache: 'no-store',
          headers: { 'Range': 'bytes=0-' }
        })
        if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`)
        const blob = await res.blob()
        zip.file(videoName, blob)
      } catch (e) {
        console.warn('视频下载失败，已跳过：', { videoName, fullUrl, error: e })
      }
    }

    // 谱面文件
    await fetchAndAdd(chart.chart_file_url, 'maidata.txt')

    const content = await zip.generateAsync({ type: 'blob' })
    saveAs(content, `${sanitizeFilename(chart.song.title)}_chart.zip`)
    ElMessage.success('谱面包下载成功')
  } catch (error) {
    console.error('下载谱面失败:', error)
    ElMessage.error('下载谱面失败')
  }
}

// ==================== 加载数据 ====================
const checkChartingPhase = async () => {
  try {
    const phase = await getCurrentPhase()
    currentPhase.value = phase
    currentPhaseName.value = phase.name || '未知'
    
    // 检查是否在制谱期（假设 phase_key 包含 'mapping' 或 'chart'）
    isChartingPhase.value = phase.page_access?.charts === true || 
                            phase.phase_key?.includes('mapping') ||
                            phase.phase_key?.includes('chart')
  } catch (error) {
    console.error('检查阶段失败:', error)
    isChartingPhase.value = true // 默认允许
  }
}

const loadMyBidResult = async () => {
  resultLoading.value = true
  try {
    const res = await getBidResults()
    console.log('getBidResults 响应:', res)
    
    if (res.success && res.results && res.results.length > 0) {
      console.log('所有中标结果:', res.results)
      
      // 优先查找歌曲竞标结果（第一阶段），其次谱面竞标结果（第二阶段）
      let bidResult = res.results.find(r => r.bid_type === 'song')
      if (!bidResult) {
        console.log('未找到歌曲竞标结果，查找谱面竞标结果...')
        bidResult = res.results.find(r => r.bid_type === 'chart')
      }
      
      if (bidResult) {
        console.log('✓ 找到中标结果:', bidResult)
        myBidResult.value = bidResult
        
        // 检查是否已有谱面
        if (myBidResult.value) {
          const chartRes = await getMyCharts()
          console.log('getMyCharts 响应:', chartRes)
          
          if (chartRes.success && chartRes.charts) {
            if (myBidResult.value.bid_type === 'song') {
              // 第一阶段：按歌曲ID匹配，且is_part_one为true
              myChart.value = chartRes.charts.find(c => 
                c.song?.id === myBidResult.value.song?.id && c.is_part_one === true
              )
            } else {
              // 第二阶段（谱面竞标）：只匹配is_part_one=false的续写谱面
              myChart.value = chartRes.charts.find(c => 
                c.is_part_one === false &&
                (c.song?.id === myBidResult.value.chart?.song?.id ||
                 c.song?.title === (myBidResult.value.chart?.song?.title || myBidResult.value.chart?.song_title))
              )
            }
            console.log('匹配的谱面:', myChart.value)
          }
        }
      } else {
        console.log('✗ 没有找到任何中标结果')
        myBidResult.value = null
      }
    } else {
      console.log('✗ 没有中标结果')
      myBidResult.value = null
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

const loadMyChartBids = async () => {
  chartBidsLoading.value = true
  try {
    // 先获取竞标轮次
    const roundsResponse = await getBiddingRounds()
    if (!roundsResponse.success || !roundsResponse.rounds.length) {
      console.warn('无法获取竞标轮次')
      return
    }
    
    // 找最新的谱面竞标轮次（优先活跃，其次已完成以显示分配结果）
    let targetChartRound = roundsResponse.rounds.find(r => r.status === 'active' && r.bidding_type === 'chart')
    if (!targetChartRound) {
      // 没有活跃的，则查找最新的已完成轮次（用于显示分配结果）
      const completedChartRounds = roundsResponse.rounds.filter(r => r.status === 'completed' && r.bidding_type === 'chart')
      if (completedChartRounds.length > 0) {
        targetChartRound = completedChartRounds[0]  // 已排序，第一个是最新的
      }
    }
    
    if (!targetChartRound) {
      console.log('当前没有活跃或已完成的谱面竞标轮次')
      currentChartBidRound.value = null
      myChartBids.value = []
      return
    }
    
    // 获取该轮次的竞标
    const res = await getMyBids(targetChartRound.id)
    
    if (res.success) {
      currentChartBidRound.value = res.round || activeChartRound
      // 过滤出谱面竞标（bid_type='chart'）
      myChartBids.value = res.bids?.filter(b => b.bid_type === 'chart') || []
      maxChartBids.value = res.max_bids || 5
      
      // 调试日志：显示每个竞标的状态
      console.log('加载谱面竞标成功，总数:', myChartBids.value.length)
      myChartBids.value.forEach((bid, idx) => {
        console.log(`竞标 ${idx + 1}:`, {
          id: bid.id,
          chart_id: bid.chart?.id,
          song_title: bid.chart?.song?.title,
          amount: bid.amount,
          status: bid.status,
          bid_type: bid.bid_type
        })
      })
    }
  } catch (error) {
    console.error('加载谱面竞标失败:', error)
  } finally {
    chartBidsLoading.value = false
  }
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



// 安全获取中标结果对应的歌曲标题（兼容歌曲/谱面两种类型）
const getBidResultSongTitle = (r) => {
  if (!r) return ''
  if (r.bid_type === 'song') {
    return r.song?.title || ''
  }
  // 谱面竞标：后端已返回 chart.song 对象；兼容旧字段 chart.song_title
  return r.chart?.song?.title || r.chart?.song_title || ''
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

// 旧版下载函数已移除，统一使用上方 downloadZip
const viewCover = (chart) => {
  if (chart.cover_url) {
    currentCover.value = chart.cover_url
    coverDialogVisible.value = true
  } else {
    ElMessage.error('封面不存在')
  }
}

// ==================== 竞标谱面函数 ====================

const showChartBidDialog = async (chart) => {
  try {
    // 获取竞标轮次（从谱面竞标轮次获取）
    const roundsResponse = await getBiddingRounds()
    if (roundsResponse.success && roundsResponse.rounds.length > 0) {
      // 找活跃的谱面竞标阶段（bidding_type='chart'）
      const activeRound = roundsResponse.rounds.find(r => r.status === 'active' && r.bidding_type === 'chart')
      if (!activeRound) {
        ElMessage.warning('当前没有活跃的谱面竞标轮次')
        return
      }
      currentChartBidRound.value = activeRound
      
      // 获取用户已有的竞标数
      const bidsResponse = await getMyBids(activeRound.id)
      if (bidsResponse.success) {
        myChartBidsCount.value = (bidsResponse.bids?.filter(b => b.bid_type === 'chart') || []).length
        maxChartBids.value = bidsResponse.max_bids || 5
      }
    } else {
      ElMessage.warning('无法获取竞标信息')
      return
    }
    
    // 获取用户代币
    const profileResponse = await getUserProfile()
    if (profileResponse && profileResponse.token !== undefined) {
      userChartBidToken.value = profileResponse.token
    }
    
    // 设置竞标表单
    chartBidForm.chartId = chart.id
    chartBidForm.chartTitle = chart.song.title
    chartBidForm.designer = chart.designer
    chartBidForm.amount = null
    chartBidDialogVisible.value = true
  } catch (error) {
    console.error('获取竞标信息失败:', error)
    ElMessage.error('无法打开竞标窗口')
  }
}

const handleSubmitChartBid = async () => {
  if (!chartBidForm.chartId || !chartBidForm.amount || chartBidForm.amount <= 0) {
    ElMessage.error('请输入有效的竞标金额')
    return
  }
  
  if (myChartBidsCount.value >= maxChartBids.value) {
    ElMessage.error(`已达到最大竞标数量限制（${maxChartBids.value}）`)
    return
  }
  
  if (userChartBidToken.value < chartBidForm.amount) {
    ElMessage.error(`代币余额不足（需要${chartBidForm.amount}，现有${userChartBidToken.value}）`)
    return
  }
  
  chartBidSubmitting.value = true
  try {
    const response = await submitBid({
      chartId: chartBidForm.chartId,
      amount: chartBidForm.amount,
      roundId: currentChartBidRound.value.id
    })
    
    if (response.success) {
      ElMessage.success('谱面竞标已提交')
      chartBidDialogVisible.value = false
      // 刷新竞标列表
      await loadMyChartBids()
    }
  } catch (error) {
    console.error('竞标失败:', error)
    ElMessage.error(error.response?.data?.message || '竞标失败')
  } finally {
    chartBidSubmitting.value = false
  }
}

const handleWithdrawBid = async (bid) => {
  ElMessageBox.confirm(
    `确定要撤回对「${bid.chart.song_title}」的竞标（${bid.amount} Token）吗？`,
    '撤回竞标',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
    .then(async () => {
      try {
        const response = await deleteBid(bid.id)
        if (response.success) {
          ElMessage.success('竞标已撤回')
          // 刷新竞标列表
          await loadMyChartBids()
        }
      } catch (error) {
        console.error('撤回竞标失败:', error)
        ElMessage.error(error.response?.data?.message || '撤回竞标失败')
      }
    })
    .catch(() => {
      // 用户取消
    })
}

const downloadChart = (chart) => {
  if (!chart.chart_file_url) {
    ElMessage.error('谱面文件不可用')
    return
  }
  downloadZip(chart)
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

// 滚动到谱面列表
const scrollToCharts = () => {
  document.querySelector('.charts-list-card')?.scrollIntoView({ 
    behavior: 'smooth' 
  })
}

// ==================== 生命周期 ====================
onMounted(async () => {
  await checkChartingPhase()
  await loadMyBidResult()
  await loadCharts()
  await loadMyChartBids()
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

.my-bids-card {
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

.round-info {
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
  flex-direction: row;
  gap: 10px;
  justify-content: center;
}

.chart-actions .el-button {
  flex: 1;
  min-width: 80px;
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


/* 新增：展开区域容器 */
.chart-details-expand {
  padding: 0 15px 15px;
}

/* 复用 Songs.vue 的暗色主题适配样式 */
.bids-section {
  background-color: rgba(0, 0, 0, 0.2); 
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 10px;
  border: 1px solid var(--border-color);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: bold;
  color: var(--text-primary);
}

.no-bids {
  padding: 15px 0;
  text-align: center;
}

/* 封面遮罩层 */
.cover-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 30px;
  background: linear-gradient(to top, rgba(0,0,0,0.6), transparent);
  display: flex;
  justify-content: center;
  align-items: center;
  color: white;
}

/* 强制覆盖 Element Plus 表格样式 (暗色适配) */
:deep(.el-table) {
  background-color: transparent !important;
  color: var(--text-primary);
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.05);
  --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.1);
  --el-table-border-color: var(--border-color);
  --el-table-text-color: var(--text-primary);
  --el-table-header-text-color: var(--text-primary);
}

:deep(.el-table th),
:deep(.el-table tr),
:deep(.el-table td) {
  background-color: transparent !important;
  border-bottom-color: var(--border-color) !important;
}

/* 高亮我的出价 */
:deep(.el-table .my-bid-row) {
  background-color: rgba(122, 200, 255, 0.15) !important;
}

:deep(.el-table .my-bid-row:hover > td.el-table__cell) {
  background-color: rgba(122, 200, 255, 0.25) !important;
}

:deep(.el-table__cell) {
  color: var(--text-secondary);
}

.highlight-self {
  font-weight: bold;
  color: var(--primary-color) !important;
}

.highlight-price {
  font-weight: bold;
  color: var(--warning-color) !important;
}

.time-text {
  font-size: 12px;
  color: var(--text-secondary) !important;
}
</style>
