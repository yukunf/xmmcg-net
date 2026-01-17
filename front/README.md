# XMMCG 前端项目

基于 Vue 3 + Vite + Element Plus 的谱面创作竞赛平台前端。

## 技术栈

- Vue 3 (Composition API)
- Vue Router 4
- Element Plus
- Axios
- Vite

## 安装依赖

```bash
npm install
```

## 开发运行

```bash
npm run dev
```

访问 http://localhost:5173

## 构建生产版本

```bash
npm run build
```

## 项目结构

```
src/
├── main.js           # 入口文件
├── App.vue           # 根组件
├── router/           # 路由配置
├── views/            # 页面组件
├── components/       # 公共组件
├── api/              # API 请求
├── assets/           # 静态资源
└── styles/           # 样式文件
```

## 功能模块

- 首页：比赛状态、轮换Banner、富文本公告
- 歌曲管理
- 谱面管理
- 用户认证（登录/注册）
- 个人中心
