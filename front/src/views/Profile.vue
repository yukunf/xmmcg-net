<template>
  <div class="profile-page">
    <el-container>
      <el-main>
        <el-card>
          <template #header>
            <div class="card-header">
              <el-icon><User /></el-icon>
              <span>个人中心</span>
            </div>
          </template>
          
          <el-descriptions :column="2" border>
            <el-descriptions-item label="用户名">
              {{ userInfo.username }}
            </el-descriptions-item>
            <el-descriptions-item label="邮箱">
              {{ userInfo.email || 'N/A' }}
            </el-descriptions-item>
            <el-descriptions-item label="注册时间">
              {{ formatDate(userInfo.date_joined) }}
            </el-descriptions-item>
            <el-descriptions-item label="剩余代币">
              <el-tag type="warning">{{ userInfo.token || 0 }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="QQ号">
              {{ userInfo.qqid || 'N/A' }}
            </el-descriptions-item>
            <el-descriptions-item label="谱师名义">
              {{ userInfo.preferred_name || '（未设置）' }}
              <el-button link size="small" style="margin-left: 8px;" @click="openEditDialog">编辑</el-button>
            </el-descriptions-item>
          </el-descriptions>

          <el-dialog v-model="editDialogVisible" title="修改谱师名义" width="400px">
            <el-form>
              <el-form-item label="谱师名义">
                <el-input
                  v-model="editForm.preferred_name"
                  maxlength="50"
                  show-word-limit
                  placeholder="留空则不展示"
                />
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="editDialogVisible = false">取消</el-button>
              <el-button type="primary" :loading="editLoading" @click="savePreferredName">保存</el-button>
            </template>
          </el-dialog>

          <el-divider />

          <el-row :gutter="20">
            <el-col :xs="24" :sm="12">
              <el-statistic title="上传歌曲" :value="userInfo.songsCount || 0">
                <template #suffix>首</template>
              </el-statistic>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-statistic title="提交谱面" :value="userInfo.chartsCount || 0">
                <template #suffix>份</template>
              </el-statistic>
            </el-col>
          </el-row>

          <el-divider />

          <div class="action-buttons">
            <el-button type="primary" @click="$router.push('/songs')">
              <el-icon><Headset /></el-icon>
              我的歌曲
            </el-button>
            <el-button type="success" @click="$router.push('/charts')">
              <el-icon><Document /></el-icon>
              我的谱面
            </el-button>
            <el-button type="danger" @click="handleLogout">
              <el-icon><SwitchButton /></el-icon>
              退出登录
            </el-button>
          </div>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import { User, Headset, Document, SwitchButton } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUserProfile, updateUserProfile } from '../api'

const router = useRouter()

const userInfo = ref({
  username: localStorage.getItem('username') || '未知用户',
  qqid: null,
  preferred_name: '',
  email: null,
  date_joined: null,
  token: 0,
  songsCount: 0,
  chartsCount: 0
})

const editDialogVisible = ref(false)
const editLoading = ref(false)
const editForm = ref({ preferred_name: '' })

const openEditDialog = () => {
  editForm.value.preferred_name = userInfo.value.preferred_name || ''
  editDialogVisible.value = true
}

const savePreferredName = async () => {
  editLoading.value = true
  try {
    await updateUserProfile({ preferred_name: editForm.value.preferred_name })
    userInfo.value.preferred_name = editForm.value.preferred_name
    editDialogVisible.value = false
    ElMessage.success('谱师名义已更新')
  } catch {
    ElMessage.error('保存失败，请重试')
  } finally {
    editLoading.value = false
  }
}

const fetchUserProfile = async () => {
  try {
    const data = await getUserProfile()
    console.log('User Profile API response:', data)
    userInfo.value = {
      ...userInfo.value,
      ...data
    }
  } catch (error) {
    console.error('获取用户信息失败:', error)
  }
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  try {
    const date = new Date(dateString)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dateString
  }
}

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    
    ElMessage.success('已退出登录')
    router.push('/')
  } catch {
    // 用户取消
  }
}

onMounted(() => {
  fetchUserProfile()
})

onActivated(() => {
  // 每次返回此页面时刷新用户信息
  fetchUserProfile()
})
</script>

<style scoped>
.profile-page {
  max-width: 1000px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: bold;
}

.action-buttons {
  margin-top: 20px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
</style>
