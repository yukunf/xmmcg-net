<template>
  <div class="eval-container">
    <el-card class="header-card">
      <div class="header">
        <h3>
          <el-icon><Edit /></el-icon>
          评分任务
        </h3>
        <el-alert
          :title="`当前允许的分数最大值：${maxScore} 分`"
          type="info"
          :closable="false"
          show-icon
        />
      </div>
    </el-card>

    <!-- 权限提示 -->
    <el-alert
      v-if="!canReview"
      title="只有提交过完成稿谱面的用户可以进行评分"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 20px;"
    />

    <!-- 加载中 -->
    <el-skeleton v-if="loading" :rows="5" animated />

    <!-- 评分任务列表 -->
    <div v-else-if="canReview" class="tasks-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>我的评分任务（{{ reviewTasks.length }}）</span>
            <el-button type="primary" size="small" @click="showAddExtraDialog">
              添加额外谱面
            </el-button>
          </div>
        </template>

        <el-empty v-if="reviewTasks.length === 0" description="暂无评分任务" />
        
        <div v-else class="tasks-list">
        <div 
          v-for="(task, index) in reviewTasks" 
          :key="task.allocation_id || `extra-${task.chart_id}`"
          class="task-item"
        >
          <div class="task-info">
            <span class="task-title">{{ getTaskDisplayName(task) }}</span>
            <el-tag v-if="task.isExtra" type="warning" size="small" style="margin-left: 10px;">额外</el-tag>
          </div>
          
          <div class="task-actions" style="display: flex; align-items: center;">
            <el-input
              v-model="task.comment"
              type="textarea"
              :rows="1"
              autosize
              placeholder="请输入评语"
              style="width: 300px; margin-right: 15px;"
            />

            <el-input-number
              v-model="task.score"
              :min="0"
              :max="maxScore"
              :precision="0"
              :step="1"
              placeholder="请输入分数"
              style="width: 150px;"
            />

            <el-tooltip :content="task.favorite ? '取消真爱票' : '设为真爱票'" placement="top">
              <el-button
                type="text"
                @click="task.favorite = !task.favorite"
                style="margin-left: 10px; font-size: 24px; padding: 0;"
              >
                <i 
                  :class="task.favorite ? 'el-icon-s-heart' : 'el-icon-heart'"
                  :style="{ color: task.favorite ? '#F56C6C' : '#C0C4CC', transition: 'color 0.3s' }"
                ></i>
              </el-button>
            </el-tooltip>
            <el-button 
              v-if="task.isExtra" 
              type="danger" 
              size="small" 
              @click="removeExtraTask(index)"
              style="margin-left: 10px;"
            >
              删除
            </el-button>
          </div>
        </div>
      </div>

        <div v-if="reviewTasks.length > 0" class="submit-section">
          <el-button 
            type="success" 
            size="large"
            :loading="submitting"
            @click="submitReviews"
          >
            提交评分
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 添加额外谱面对话框 -->
    <el-dialog 
      v-model="extraDialogVisible" 
      title="添加额外谱面" 
      width="600px"
    >
      <el-select 
        v-model="selectedExtraChart" 
        placeholder="请选择要评分的谱面" 
        filterable
        style="width: 100%;"
      >
        <el-option
          v-for="chart in availableCharts"
          :key="chart.id"
          :label="getChartDisplayName(chart)"
          :value="chart.id"
        />
      </el-select>
      
      <template #footer>
        <el-button @click="extraDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addExtraTask">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>


<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit } from '@element-plus/icons-vue'
import { getPeerReviewConfig, getMyReviewTasks, submitReview, submitExtraReview, getMyCharts, getCharts } from '../api'
import { fa } from 'element-plus/es/locale/index.mjs'

const loading = ref(true)
const submitting = ref(false)
const canReview = ref(false)
const maxScore = ref(50)
const reviewTasks = ref([])

// 额外评分相关
const extraDialogVisible = ref(false)
const selectedExtraChart = ref(null)
const availableCharts = ref([])

// 加载配置和任务
const loadData = async () => {
  loading.value = true
  try {
    // 1. 获取最大分数配置
    const statusRes = await getPeerReviewConfig()
    maxScore.value = statusRes.peer_review_max_score || 50

    // 2. 直接获取评分任务（不需要round_id）
    const tasksRes = await getMyReviewTasks()
    
    if (!tasksRes.success) {
      ElMessage.warning(tasksRes.message || '获取评分任务失败')
      loading.value = false
      return
    }

    // 处理评分任务数据
    reviewTasks.value = tasksRes.tasks?.map(task => ({
      allocation_id: task.id,  // 后端返回的id就是allocation_id
      chart_id: task.chart_id,
      chart_title: task.song_title,
      designer: task.chart_designer || '未知谱师',  // 添加谱师信息
      score: null,
      comments: '',
      favorite: false,
      isExtra: false  // 系统分配的任务不是额外任务
    })) || []
    
    // 如果有任务，允许评分
    canReview.value = reviewTasks.value.length > 0

  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error(error.response?.data?.message || '加载数据失败')
  } finally {
    loading.value = false
  }
}

// 验证评分数据
const validateScores = () => {
  for (let i = 0; i < reviewTasks.value.length; i++) {
    const task = reviewTasks.value[i]
    
    if (task.score === null || task.score === undefined || task.score === '') {
      ElMessage.warning(`请为「${task.chart_title}」填写分数`)
      return false
    }

    if (task.score < 0) {
      ElMessage.warning(`「${task.chart_title}」的分数不能为负数`)
      return false
    }

    if (task.score > maxScore.value) {
      ElMessage.warning(`"${task.chart_title}"的分数不能超过${maxScore.value}分`)
      return false
    }

    if (!Number.isInteger(task.score)) {
      ElMessage.warning(`"${task.chart_title}"的分数必须为整数`)
      return false
    }
  }

  return true
}

// 提交评分
const submitReviews = async () => {
  if (!validateScores()) {
    return
  }

  // 分离系统任务和额外任务
  const systemTasks = reviewTasks.value.filter(task => task.allocation_id !== null)
  const extraTasks = reviewTasks.value.filter(task => task.isExtra)
  const totalTasks = systemTasks.length + extraTasks.length
  
  if (totalTasks === 0) {
    ElMessage.warning('没有可提交的评分')
    return
  }

  try {
    let confirmMsg = `确定要提交 ${totalTasks} 个评分吗？`
    if (systemTasks.length > 0 && extraTasks.length > 0) {
      confirmMsg += `\n其中：${systemTasks.length} 个系统分配任务，${extraTasks.length} 个额外评分。`
    }
    confirmMsg += '\n提交后将无法修改。'
    
    await ElMessageBox.confirm(
      confirmMsg,
      '确认提交',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    submitting.value = true

    // 提交系统分配的任务
    const systemPromises = systemTasks
      .filter(task => task.score !== null && task.score !== '')
      .map(task => submitReview(task.allocation_id, task.score, task.comments, task.favorite))

    // 提交额外评分
    const extraPromises = extraTasks
      .filter(task => task.score !== null && task.score !== '')
      .map(task => submitExtraReview(task.chart_id, task.score, task.comments, task.favorite))

    // 并发提交所有评分
    await Promise.all([...systemPromises, ...extraPromises])

    ElMessage.success(`评分提交成功！已提交 ${totalTasks} 个评分`)
    
    // 重新加载数据
    await loadData()

  } catch (error) {
    if (error === 'cancel') {
      return
    }
    console.error('提交失败:', error)
    ElMessage.error(error.response?.data?.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadData()
})

// 生成任务显示名称（如果标题重复则附加谱师名义）
const getTaskDisplayName = (task) => {
  const title = task.chart_title || '未知标题'
  const designer = task.designer || '未知谱师'
  
  // 检查是否有其他任务使用相同标题
  const sameTitleTasks = reviewTasks.value.filter(t => t.chart_title === task.chart_title)
  
  // 如果有重复标题，附加谱师名义
  if (sameTitleTasks.length > 1) {
    return `${title} [${designer}]`
  }
  
  return title
}

// 生成谱面显示名称（如果标题重复则附加谱师名义）
const getChartDisplayName = (chart) => {
  const title = chart.song_title || '未知标题'
  const designer = chart.designer || '未知谱师'
  
  // 检查是否有其他谱面使用相同标题
  const sameTitleCharts = availableCharts.value.filter(c => c.song_title === chart.song_title)
  
  // 如果有重复标题，附加谱师名义
  if (sameTitleCharts.length > 1) {
    return `${title} [${designer}]`
  }
  
  return title
}

// 显示添加额外谱面对话框
const showAddExtraDialog = async () => {
  try {
    // 获取所有谱面（不需要round_id）
    const res = await getCharts()
    
    // 过滤掉已经在任务列表中的谱面
    const existingChartIds = reviewTasks.value.map(t => t.chart_id)
    availableCharts.value = (res.results || res || []).filter(
      chart => !existingChartIds.includes(chart.id)
    )
    
    if (availableCharts.value.length === 0) {
      ElMessage.warning('没有更多谱面可以添加')
      return
    }
    
    extraDialogVisible.value = true
  } catch (error) {
    console.error('获取谱面列表失败:', error)
    ElMessage.error('获取谱面列表失败')
  }
}

// 添加额外任务
const addExtraTask = () => {
  if (!selectedExtraChart.value) {
    ElMessage.warning('请选择要评分的谱面')
    return
  }
  
  const chart = availableCharts.value.find(c => c.id === selectedExtraChart.value)
  if (!chart) return
  
  reviewTasks.value.push({
    allocation_id: null, // 额外任务没有allocation_id
    chart_id: chart.id,
    chart_title: chart.song_title,
    designer: chart.designer || '未知谱师',  // 添加谱师信息
    score: null,
    comments: '',
    favorite: false,
    isExtra: true
  })
  
  ElMessage.success(`已添加「${chart.song_title}」到评分任务`)
  extraDialogVisible.value = false
  selectedExtraChart.value = null
}

// 删除额外任务
const removeExtraTask = (index) => {
  const task = reviewTasks.value[index]
  reviewTasks.value.splice(index, 1)
  ElMessage.info(`已移除「${task.chart_title}」`)
}
</script>

<style scoped>
.eval-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.header-card {
  margin-bottom: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}

.header h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
  flex-shrink: 0;
}

.tasks-section {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.task-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 8px;
  transition: all 0.3s;
}

.task-item:hover {
  background-color: #e8eaf0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.task-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.task-designer {
  font-size: 14px;
  color: #909399;
}

.task-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.submit-section {
  margin-top: 30px;
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #dcdfe6;
}
</style>
