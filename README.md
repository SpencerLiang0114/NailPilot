# Nail Art World Cup｜美甲 AI 试戴与智能运营

> 美团黑客松参赛项目，面向赛题「美甲 AI 试戴与智能运营」。  
> 本项目将用户端 AI 美甲试戴与商家端趋势运营连接成一个完整闭环：用户通过上传手部照片获得真实试戴效果，商家则基于趋势数据生成热点日报、款式排序建议和可执行运营动作。

---

## 项目简介

美甲消费的核心问题并不是“款式不够多”，而是用户和商家都缺少实时、直观、可执行的判断依据。

在用户端，消费者很难提前判断一款美甲是否适合自己的肤色、手型和风格，因此容易出现决策时间长、沟通成本高、下单转化低的问题。

在商家端，门店通常依赖人工观察社交平台趋势、手动调整推荐位和款式排序，容易出现趋势识别滞后、热门款错过最佳运营窗口、内容发布与商品上新脱节等问题。

本项目尝试构建一个可运行的闭环系统：

1. **用户端**：提供 AI 美甲试戴，降低用户决策成本。
2. **运营端**：根据趋势数据生成美甲热点日报和运营建议。
3. **业务闭环**：让用户试戴结果、推荐款式池和商家运营策略随热点变化动态更新。

---

## 核心功能

### 1. 用户端：AI 美甲试戴应用

访问路径：

```text
/user
```

主要能力：

- 支持用户上传手部照片。
- 支持从本地商品库中选择美甲款式。
- 调用 FastAPI 后端生成 AI 美甲试戴图。
- 根据当前试戴款式生成 8 款相似推荐。
- 使用商品 ID 作为推荐、试戴和展示的统一集成键，避免只依赖图片 URL 或展示名称。

当前商品数据来自：

```text
backend/nail-tryon-ai/products.json
```

目前内置 57 款初始美甲商品。

---

### 2. 运营端：AI 助手智能运营

访问路径：

```text
/ops/manicure-hotspots
```

主要能力：

- 支持输入关键词，例如 `美甲`、`猫眼`、`穿戴甲`。
- 对趋势数据进行美甲相关性过滤、去重和打分。
- 生成热点榜、趋势图、当天热点总结和运营日报。
- 输出可执行运营建议，包括：
  - 首页推荐位调整
  - 款式列表排序
  - 内容发布计划
  - AI 试戴款式池更新
  - 商家 todo list

数据源说明：

- 项目预留小红书趋势数据接入能力。
- 真实趋势数据需要通过合规 API、平台授权或第三方数据服务接入。
- 当真实数据源未配置、不可用或额度不足时，系统会返回明确标记的模拟报告。
- 前端会同步展示“模拟数据”提示，避免将降级数据误认为真实趋势。

---

### 3. 门户页

访问路径：

```text
/
```

门户页作为参赛作品入口，提供两个核心入口：

- 用户端 AI 美甲试戴
- 商家端智能运营面板

---

## Demo Flow

### 用户端流程

```text
用户打开 /user
        ↓
加载美甲商品库
        ↓
上传手部照片
        ↓
选择美甲款式
        ↓
调用 AI 试戴后端
        ↓
生成试戴结果图
        ↓
返回相似款推荐
```

### 运营端流程

```text
商家打开 /ops/manicure-hotspots
        ↓
输入趋势关键词
        ↓
获取趋势数据
        ↓
过滤美甲相关内容
        ↓
计算热点分数
        ↓
生成热点日报
        ↓
输出运营建议和执行清单
```

---

## 系统架构

```text
Next.js App Router
├── /
│   └── 项目门户页
│
├── /user
│   ├── GET  /api/user/initial-products
│   ├── POST /api/user/nail-tryon
│   └── POST /api/user/recommendations
│
├── /ops/manicure-hotspots
│   └── GET /api/ops/manicure-hotspots
│
└── FastAPI Backend
    ├── GET  /api/initial_products
    ├── POST /api/nail_tryon
    └── POST /recommendations
```

---

## 技术栈

### Frontend

- Next.js App Router
- React
- TypeScript
- Tailwind CSS

### Backend

- FastAPI
- Python
- Local AI try-on pipeline
- Local product recommendation logic

### Data & Recommendation

- 本地美甲商品库
- 趋势数据适配层
- 美甲相关性过滤
- 热度、增长、新颖性、转化潜力等多维度打分
- 模拟数据降级策略

---

## 后端试戴模型流程

后端试戴模型负责将“美甲商品图”和“用户手部照片”对齐到同一空间，并生成自然贴合的虚拟佩戴效果。

整体流程分为三步：

### 1. 分割与目标剥离

模型首先识别：

- 商品图中的美甲区域
- 用户手部照片中的指甲区域

随后生成对应的 segmentation mask，将美甲款式从原始背景中剥离出来，形成可单独处理的美甲素材。

### 2. 手部姿态与边界估计

系统结合手部关键点和指甲区域 mask，估计每根手指的：

- 指尖位置
- 指甲边界
- 手指方向
- 旋转角度
- 目标贴合区域

这些信息用于确定美甲素材在用户手部照片中的位置、角度和尺寸。

### 3. 对齐、缩放与融合

后端根据目标指甲区域对美甲素材进行：

- 旋转
- 平移
- 自适应缩放
- 边界融合

最终生成 AI 美甲试戴图。

本流程的目标不是简单贴图，而是在保留商品纹理、颜色和风格的同时，使试戴结果在方向、大小和边界上尽量接近真实佩戴效果。

---

## 代码结构

```text
src/
├── app/
│   ├── page.tsx
│   ├── user/page.tsx
│   ├── merchant/page.tsx
│   ├── ops/manicure-hotspots/page.tsx
│   └── api/
│       ├── user/
│       │   ├── initial-products
│       │   ├── nail-tryon
│       │   └── recommendations
│       └── ops/manicure-hotspots
│
├── components/
│   └── ops/
│
├── services/
│   ├── trend fetching
│   ├── trend filtering
│   ├── scoring
│   └── report generation
│
└── backend/
    └── nail-tryon-ai/
        ├── api.py
        ├── run_pipeline.py
        ├── recommender.py
        ├── products.json
        └── 美甲图74个/
```

---

## 本地运行

项目需要同时启动前端和后端两个进程。

默认地址：

```text
Next.js 前端:      http://127.0.0.1:3000
FastAPI 后端:     http://127.0.0.1:8000
```

常用页面：

```text
作品入口:          http://127.0.0.1:3000
用户试戴:          http://127.0.0.1:3000/user
运营面板:          http://127.0.0.1:3000/ops/manicure-hotspots
```

---

## macOS 启动方式

### 1. 启动前端

```bash
pnpm install
cp .env.example .env.local
pnpm exec next dev --hostname 127.0.0.1 --port 3000
```

### 2. 启动后端

```bash
cd backend/nail-tryon-ai

uv venv
uv pip install -r requirements.txt

export NAIL_TRYON_SAM3_WEIGHTS=/absolute/path/sam3.pt
export NAIL_TRYON_SD_INPAINTING_DIR=/absolute/path/stable-diffusion-inpainting
export NAIL_TRYON_PUBLIC_BASE_URL=http://127.0.0.1:8000

.venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

也可以使用脚本启动：

```bash
cd backend/nail-tryon-ai
./start_backend.sh
```

---

## Windows 启动方式

建议将仓库放在简单英文路径下，例如：

```text
D:\projects\Beauty_Nai1s-merchants
```

### 1. 启动前端

```powershell
pnpm install
copy .env.example .env.local
pnpm exec next dev --hostname 127.0.0.1 --port 3000
```

### 2. 启动后端

```powershell
cd backend\nail-tryon-ai

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

$env:NAIL_TRYON_SAM3_WEIGHTS="D:\models\sam3\sam3.pt"
$env:NAIL_TRYON_SD_INPAINTING_DIR="D:\models\stable-diffusion-inpainting"
$env:NAIL_TRYON_PUBLIC_BASE_URL="http://127.0.0.1:8000"

python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

如果 Windows 机器有 NVIDIA GPU，请安装匹配 CUDA 版本的 PyTorch，并检查 GPU 是否可用：

```powershell
python -c "import torch; print(torch.cuda.is_available())"
```

---

## 环境变量

### 前端 `.env.local`

可从 `.env.example` 复制：

```env
NAIL_TRYON_API_BASE_URL=http://127.0.0.1:8000

# 可选：趋势数据 API token
XHS_API_TOKEN=
```

### 后端环境变量

后端模型路径通过 shell 环境变量配置，不应暴露给浏览器：

```env
NAIL_TRYON_SAM3_WEIGHTS=/absolute/path/sam3.pt
NAIL_TRYON_SD_INPAINTING_DIR=/absolute/path/stable-diffusion-inpainting
NAIL_TRYON_PUBLIC_BASE_URL=http://127.0.0.1:8000
```

请不要提交以下内容：

```text
.env.local
真实 API key
本地模型权重
生成结果目录
临时缓存文件
```

---

## 数据与降级策略

### 用户试戴

用户试戴流程依赖 FastAPI 后端和本地模型路径。

如果模型路径未配置或模型文件不存在，后端会返回错误信息，前端应提示用户检查后端环境变量和模型文件路径。

### 运营日报

运营日报支持真实数据源和模拟数据降级。

当真实 API 不可用时，接口仍会返回结构完整的报告，但会标记为：

```json
{
  "dataSource": "simulated",
  "isSimulated": true
}
```

前端会根据该字段展示模拟数据提示。

这样可以保证：

- 演示流程不中断。
- 页面结构保持完整。
- 真实数据和模拟数据不会混淆。
- 后续接入真实趋势数据时不需要重构前端展示层。

---

## 验证命令

### 前端

```bash
pnpm run lint
pnpm run typecheck
pnpm run build
```

### 后端

```bash
cd backend/nail-tryon-ai

.venv/bin/python -m py_compile api.py run_pipeline.py recommender.py
curl http://127.0.0.1:8000/health
```

---

## 评审标准对应

### 完整性

项目覆盖用户端、商家端和门户页，不是单一页面 demo。

已实现能力包括：

- 用户上传手部照片
- 美甲款式选择
- AI 试戴生成
- 相似款推荐
- 运营日报生成
- 热点榜和趋势图
- 商家执行建议
- 真实数据接入预留
- 模拟数据降级

### 创新性

项目将“AI 上手效果可视化”和“AI 运营决策自动化”结合在同一业务闭环中。

用户侧的试戴数据可以反向影响商家侧的推荐位、款式池和运营重点；商家侧的热点识别也可以进一步影响用户侧的商品展示和推荐策略。

### 应用效果

用户可以直接上传图片体验美甲试戴，降低下单前的不确定性。

商家可以通过热点日报快速了解当天趋势，并获得具体到推荐位、款式排序、内容发布和库存动作的执行建议。

### 商业价值

项目能够帮助平台和商家：

- 降低用户决策成本
- 提高美甲款式转化效率
- 缩短热点识别到运营执行的时间
- 优化首页推荐位和商品排序
- 支持门店上新、内容运营和库存准备

---

## 公开仓库说明

本项目为黑客松参赛原型，重点展示完整业务链路和可运行的核心能力。

公开仓库不包含：

- 真实模型权重
- 真实 API key
- `.env.local`
- 本地生成资产
- 私有数据文件

后端真实试戴功能依赖以下环境变量指向有效本地模型：

```env
NAIL_TRYON_SAM3_WEIGHTS
NAIL_TRYON_SD_INPAINTING_DIR
```

未配置趋势 API token 时，运营端会展示明确标记的模拟报告。

---

## Project Status

当前版本已完成：

- 用户端 AI 美甲试戴主流程
- FastAPI 后端试戴接口
- 商品库加载
- 相似款推荐
- 商家端热点运营面板
- 热点日报生成
- 模拟数据降级
- 门户页入口

后续可扩展方向：

- 接入稳定的真实趋势数据源
- 增加用户试戴偏好记录
- 引入更精细的手型、肤色和风格匹配算法
- 将运营端建议与商品管理、库存和发布系统联动
- 增加商家侧 A/B 测试和转化数据反馈