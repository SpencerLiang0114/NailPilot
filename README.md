# Nail Art World Cup｜美甲 AI 试戴与智能运营

美团黑客松参赛项目，面向赛题「美甲 AI 试戴与智能运营」。

本项目尝试把用户端的 AI 美甲试戴和商家端的热点运营串成一个可落地的闭环：用户上传手部照片后选择美甲款式，系统生成上手试戴效果并推荐相似款；商家侧则根据小红书/Rnote 趋势数据生成美甲热点日报、款式排序建议和运营执行清单。

## 赛题背景

美甲消费的核心问题不是“有没有款式”，而是用户和商家都缺少实时、直观、可执行的判断依据。

用户侧痛点：

- 无法预见真实上手效果，担心款式与肤色、手型不匹配。
- 线下试戴和沟通成本高，决策周期长，容易放弃下单。
- 款式很多但选择困难，需要更贴近当前偏好的推荐。

运营侧痛点：

- 热门款识别依赖人工观察，滞后且容易错过运营窗口。
- 推荐位、款式列表、内容发布和库存动作缺少统一决策依据。
- 用户“所见”和商家“所感知”的趋势之间存在信息延迟。

项目目标是构建一个完整系统，而不是单点 demo：

1. 用户端：提供可视化的 AI 美甲试戴体验，降低决策成本。
2. 运营端：把趋势洞察转成日报、榜单和具体执行动作。
3. 闭环：让试戴款式池、推荐位和商家运营策略随热点变化而更新。

## 已实现功能

### 用户端：AI 美甲试戴应用

访问路径：`/user`

- 从后端加载美甲商品库，当前使用 `products.json` 中的 57 款初始款式。
- 支持用户上传手部照片，并在页面中预览。
- 支持选择美甲款式后调用 FastAPI 后端生成真实试戴图。
- 试戴完成后，根据当前款式 ID 生成 8 款个性化推荐，并替换原款式轮播。
- 保留商品 ID 作为推荐和试戴的集成键，避免只依赖图片 URL 或展示名称。

### 运营端：AI 助手智能运营

访问路径：`/ops/manicure-hotspots`

- 支持输入关键词，如 `美甲`、`猫眼`、`穿戴甲`，手动生成运营日报。
- 接入 Rnote/小红书趋势接口，拉取热搜和关键词内容。
- 对趋势数据进行美甲相关性过滤、去重和打分。
- 生成热点榜、趋势图、当天热点总结和运营日报。
- 输出可执行建议，包括首页推荐位、款式列表排序、内容发布计划、AI 试戴款式池更新和商家 todo。
- 当真实 API 不可用、未配置或额度不足时，返回明确标记的模拟报告，页面会显示“模拟数据”提示。

### 门户页

访问路径：`/`

- 提供用户端和商家端入口。
- 以 Nail Art World Cup 作为参赛作品入口品牌。

## 系统架构

```text
Next.js App Router
├── /user
│   ├── GET  /api/user/initial-products
│   ├── POST /api/user/nail-tryon
│   └── POST /api/user/recommendations
├── /ops/manicure-hotspots
│   └── GET /api/ops/manicure-hotspots
└── FastAPI Backend
    ├── /api/initial_products
    ├── /api/nail_tryon
    └── /recommendations
```

主要技术栈：

- Next.js App Router
- React
- TypeScript
- FastAPI
- Python AI 试戴 pipeline
- Rnote/小红书数据 API
- 本地美甲商品库与推荐逻辑

## 代码结构

```text
src/app/page.tsx                         # 入口门户
src/app/user/page.tsx                    # 用户端 AI 试戴页面
src/app/merchant/page.tsx                # 商家端跳转入口
src/app/ops/manicure-hotspots/page.tsx   # 运营端热点面板
src/app/api/user/*                       # 用户端 Next.js 代理 API
src/app/api/ops/manicure-hotspots        # 运营日报生成 API
src/components/ops/*                     # 运营端展示组件
src/services/*                           # 趋势拉取、过滤、打分、报告生成
backend/nail-tryon-ai/api.py             # FastAPI 试戴与推荐服务
backend/nail-tryon-ai/run_pipeline.py    # AI 试戴 pipeline 入口
backend/nail-tryon-ai/products.json      # 美甲商品数据
backend/nail-tryon-ai/美甲图74个          # 本地美甲款式图
```

## 本地运行

项目需要同时启动前端和后端两个进程：

- Next.js 前端：`http://127.0.0.1:3000`
- FastAPI 试戴后端：`http://127.0.0.1:8000`

常用页面：

- 作品入口：`http://127.0.0.1:3000`
- 用户试戴：`http://127.0.0.1:3000/user`
- 运营面板：`http://127.0.0.1:3000/ops/manicure-hotspots`

### macOS

启动前端：

```bash
pnpm install
cp .env.example .env.local
pnpm exec next dev --hostname 127.0.0.1 --port 3000
```

启动后端：

```bash
cd backend/nail-tryon-ai
uv venv
uv pip install -r requirements.txt
export NAIL_TRYON_SAM3_WEIGHTS=/absolute/path/sam3.pt
export NAIL_TRYON_SD_INPAINTING_DIR=/absolute/path/stable-diffusion-inpainting
export NAIL_TRYON_PUBLIC_BASE_URL=http://127.0.0.1:8000
.venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

也可以使用脚本启动后端：

```bash
cd backend/nail-tryon-ai
./start_backend.sh
```

### Windows

建议将仓库放在简单英文路径，例如 `D:\projects\Beauty_Nai1s-merchants`。

启动前端：

```powershell
pnpm install
copy .env.example .env.local
pnpm exec next dev --hostname 127.0.0.1 --port 3000
```

启动后端：

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

如果 Windows 机器有 NVIDIA GPU，请安装匹配 CUDA 版本的 PyTorch，并检查：

```powershell
python -c "import torch; print(torch.cuda.is_available())"
```

## 环境变量

前端 `.env.local` 可从 `.env.example` 复制：

```env
XHS_API_BASE_URL=https://rnote.dev
XHS_API_TOKEN=
XHS_HOT_SEARCH_ENDPOINT=/api/v2/crawler/creator/hot/inspiration/feed
XHS_KEYWORD_SEARCH_ENDPOINT=/api/v2/crawler/search/notes
XHS_API_AUTH_HEADER=X-API-Key
XHS_API_AUTH_SCHEME=
XHS_API_METHOD=GET
XHS_API_EXTRA_HEADERS=
XHS_HOT_SEARCH_PAGE_SIZE=50
XHS_KEYWORD_SEARCH_PAGE_SIZE=20

NAIL_TRYON_API_BASE_URL=http://127.0.0.1:8000
```

后端模型路径通过 shell 环境变量配置，不应暴露给浏览器：

```env
NAIL_TRYON_SAM3_WEIGHTS=/absolute/path/sam3.pt
NAIL_TRYON_SD_INPAINTING_DIR=/absolute/path/stable-diffusion-inpainting
NAIL_TRYON_PUBLIC_BASE_URL=http://127.0.0.1:8000
```

不要提交 `.env.local`、真实 API key、本地模型权重或生成结果目录。

## 数据与降级策略

### 用户试戴流程

1. 用户打开 `/user`。
2. 前端调用 `GET /api/user/initial-products` 加载美甲商品。
3. 用户选择款式并上传手部照片。
4. 前端向 `POST /api/user/nail-tryon` 提交 `product_id` 和图片文件。
5. Next.js 将请求代理到 FastAPI `POST /api/nail_tryon`。
6. FastAPI 运行 Python 试戴 pipeline 并返回生成图片。
7. 前端调用 `POST /api/user/recommendations`。
8. 页面展示 8 款推荐美甲。

### 运营日报流程

1. 商家在运营面板点击“生成报告”。
2. 后端请求 Rnote/小红书热搜和关键词接口。
3. 系统将接口返回内容标准化为趋势记录。
4. 美甲趋势过滤器筛选相关内容。
5. 打分模块按热度、相关性、增长、新颖性、商家可执行性和转化潜力排序。
6. 报告生成器输出日报、热点榜和执行建议。

真实接口失败时，API 仍会返回成功响应，但数据会标记为：

```json
{
  "dataSource": "simulated",
  "isSimulated": true
}
```

页面会同步显示模拟数据提示。真实 API 恢复后，同一页面会回到真实趋势数据。

## 验证命令

前端：

```bash
pnpm run lint
pnpm run typecheck
pnpm run build
```

后端：

```bash
cd backend/nail-tryon-ai
.venv/bin/python -m py_compile api.py run_pipeline.py recommender.py
curl http://127.0.0.1:8000/health
```

## 评审标准对应

- 完整性：包含用户端试戴、商家端日报、推荐逻辑、真实 API 接入和模拟降级。
- 创新性：把“上手效果可视化”和“热点运营自动化”放在同一业务闭环中。
- 应用效果：用户可以直接上传图片体验试戴，商家可以生成当天可执行运营动作。
- 商业价值：帮助降低用户决策成本，提高款式转化效率，并为门店上新、推荐位和内容运营提供依据。

## 公开仓库说明

- 真实模型权重、API key、`.env.local` 和本地生成资产不应提交。
- 后端真实试戴依赖 `NAIL_TRYON_SAM3_WEIGHTS` 和 `NAIL_TRYON_SD_INPAINTING_DIR` 指向有效本地模型。
- 未配置小红书/Rnote token 时，运营端会展示明确标记的模拟报告。
- 本项目是黑客松参赛原型，重点展示完整业务链路和可运行的核心能力。
