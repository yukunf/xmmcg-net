<template>
  <el-carousel :interval="5000" height="300px" class="banner-carousel">
    <el-carousel-item v-for="(item, index) in banners" :key="index">
      <div 
        class="banner-item" 
        :style="{ 
          backgroundColor: item.color,
          backgroundImage: item.image_url ? `url(${processImageUrl(item.image_url)})` : 'none',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat'
        }"
      >
        <div class="banner-content-overlay">
          <div class="banner-content">
            <h2>{{ item.title }}</h2>
            <p>{{ item.content }}</p>
            <el-button v-if="item.link" type="primary" size="large" @click="handleClick(item.link)">
              {{ item.button_text || '了解更多' }}
            </el-button>
          </div>
        </div>
      </div>
    </el-carousel-item>
  </el-carousel>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getBanners } from '../api'

const router = useRouter()

const banners = ref([])

// 处理图片URL，确保在nginx反向代理下正确访问
const processImageUrl = (url) => {
  if (!url) return null
  
  // 如果是相对路径，直接返回
  if (url.startsWith('/')) {
    return url
  }
  
  // 如果是localhost开发地址，转换为相对路径
  if (url.includes('localhost:8000')) {
    return url.replace(/https?:\/\/localhost:8000/, '')
  }
  
  // 如果是完整的服务器地址，提取路径部分
  if (url.includes('/media/') || url.includes('/static/')) {
    const pathMatch = url.match(/\/(media|static)\/.*$/)
    return pathMatch ? pathMatch[0] : url
  }
  
  // 外部URL直接返回
  return url
}

const handleClick = (link) => {
  if (link) {
    // 检查是否是内部路由
    if (link.startsWith('/')) {
      router.push(link)
    } else {
      window.open(link, '_blank')
    }
  }
}

const fetchBanners = async () => {
  try {
    const data = await getBanners()
    if (data && data.length > 0) {
      banners.value = data
    }
  } catch (error) {
    console.error('获取 Banner 失败:', error)
  }
}

onMounted(() => {
  fetchBanners()
})
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
  position: relative;
  z-index: 2;
}

.banner-content-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
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
