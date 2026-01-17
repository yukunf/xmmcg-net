<template>
  <el-carousel :interval="5000" height="300px" class="banner-carousel">
    <el-carousel-item v-for="(item, index) in banners" :key="index">
      <div class="banner-item" :style="{ backgroundColor: item.color }">
        <div class="banner-content">
          <h2>{{ item.title }}</h2>
          <p>{{ item.description }}</p>
          <el-button v-if="item.link" type="primary" size="large" @click="handleClick(item.link)">
            {{ item.buttonText || '了解更多' }}
          </el-button>
        </div>
      </div>
    </el-carousel-item>
  </el-carousel>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const banners = ref([
  {
    title: '欢迎来到 XMMCG',
    description: '谱面创作竞赛平台，展现你的创意才华',
    color: '#409EFF',
    link: '/songs',
    buttonText: '开始竞标'
  },
  {
    title: '第一轮竞标进行中',
    description: '参与歌曲竞标，赢取制谱权利',
    color: '#67C23A',
    link: '/charts',
    buttonText: '查看谱面'
  },
  {
    title: '互评系统',
    description: '公平公正的评分机制，让优秀作品脱颖而出',
    color: '#E6A23C',
    link: '/profile',
    buttonText: '个人中心'
  }
])

const handleClick = (link) => {
  if (link) {
    router.push(link)
  }
}
</script>

<style scoped>
.banner-carousel {
  margin-bottom: 20px;
  border-radius: 8px;
  overflow: hidden;
}

.banner-item {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.banner-content {
  text-align: center;
  padding: 20px;
}

.banner-content h2 {
  font-size: 36px;
  margin: 0 0 15px 0;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
}

.banner-content p {
  font-size: 18px;
  margin: 0 0 25px 0;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
}

@media (max-width: 768px) {
  .banner-content h2 {
    font-size: 24px;
  }
  
  .banner-content p {
    font-size: 14px;
  }
}
</style>
