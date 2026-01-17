<template>
  <div class="charts-page">
    <el-container>
      <el-main>
        <el-card>
          <template #header>
            <div class="card-header">
              <el-icon><Document /></el-icon>
              <span>谱面列表</span>
            </div>
          </template>
          <el-empty description="谱面列表功能开发中..." :image-size="200">
            <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
          </el-empty>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { Document } from '@element-plus/icons-vue'
</script>

<style scoped>
.charts-page {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: bold;
}
</style>
