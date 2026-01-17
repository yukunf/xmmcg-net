<template>
  <el-card class="announcement-card" shadow="hover">
    <template #header>
      <div class="card-header">
        <el-icon><BellFilled /></el-icon>
        <span>最新公告</span>
      </div>
    </template>
    
    <el-timeline>
      <el-timeline-item
        v-for="(announcement, index) in announcements"
        :key="index"
        :timestamp="announcement.time"
        :type="announcement.type"
        placement="top"
      >
        <el-card :body-style="{ padding: '15px' }">
          <h4>{{ announcement.title }}</h4>
          <div class="announcement-content" v-html="announcement.content"></div>
        </el-card>
      </el-timeline-item>
    </el-timeline>
    
    <el-empty v-if="announcements.length === 0" description="暂无公告" />
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { BellFilled } from '@element-plus/icons-vue'
import { getAnnouncements } from '../api'

const announcements = ref([
  {
    title: '第一轮竞标开始',
    content: '<p>第一轮歌曲竞标已经开始，请各位选手积极参与！</p><p><strong>注意事项：</strong></p><ul><li>每人最多可竞标5首歌曲</li><li>请合理分配您的代币</li></ul>',
    time: '2026-01-15 10:00',
    type: 'primary'
  },
  {
    title: '平台上线公告',
    content: '<p>欢迎来到 XMMCG 谱面创作竞赛平台！</p><p>本平台支持：</p><ul><li>歌曲上传与管理</li><li>竞标系统</li><li>谱面提交</li><li>互评系统</li></ul>',
    time: '2026-01-10 14:30',
    type: 'success'
  }
])

const fetchAnnouncements = async () => {
  try {
    const data = await getAnnouncements()
    if (data && data.length > 0) {
      announcements.value = data
    }
  } catch (error) {
    console.error('获取公告失败:', error)
  }
}

onMounted(() => {
  fetchAnnouncements()
})
</script>

<style scoped>
.announcement-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: bold;
}

.announcement-content {
  color: #606266;
  line-height: 1.6;
}

.announcement-content :deep(p) {
  margin: 8px 0;
}

.announcement-content :deep(ul) {
  margin: 8px 0;
  padding-left: 20px;
}

.announcement-content :deep(strong) {
  color: #303133;
  font-weight: bold;
}

.announcement-content :deep(h4) {
  margin: 10px 0;
  color: #303133;
}
</style>
