import type { ManicureHotspotsData } from "@/types/manicureHotspots";

interface SimulatedTrendSeed {
  keyword: string;
  title: string;
  hotspotScore: number;
  popularityScore: number;
  relevanceScore: number;
  growthScore: number;
  noveltyScore: number;
  merchantFeasibilityScore: number;
  conversionPotentialScore: number;
  reason: string;
  targetUsers: string[];
  suggestedStyles: string[];
  merchantActions: string[];
  recommendedPromotionCopy: string;
}

const SIMULATED_TRENDS: SimulatedTrendSeed[] = [
  {
    keyword: "显白猫眼",
    title: "模拟趋势：显白猫眼通勤款",
    hotspotScore: 88,
    popularityScore: 86,
    relevanceScore: 96,
    growthScore: 82,
    noveltyScore: 84,
    merchantFeasibilityScore: 90,
    conversionPotentialScore: 86,
    reason: "模拟数据：假设近期用户偏好显白、低调但有光泽变化的猫眼款。",
    targetUsers: ["通勤白领", "约会场景用户"],
    suggestedStyles: ["显白猫眼款式", "短甲猫眼款式", "裸色猫眼款式"],
    merchantActions: [
      "将显白猫眼放入首页第一推荐位。",
      "AI 试戴入口优先展示短甲猫眼和裸色猫眼。",
      "门店内容标题突出“显白”“通勤”“低调高级”。"
    ],
    recommendedPromotionCopy:
      "模拟文案：想要低调又显白？先试戴显白猫眼款，看不同光线下的细闪效果。"
  },
  {
    keyword: "新中式晕染",
    title: "模拟趋势：新中式晕染节日款",
    hotspotScore: 83,
    popularityScore: 78,
    relevanceScore: 94,
    growthScore: 80,
    noveltyScore: 92,
    merchantFeasibilityScore: 76,
    conversionPotentialScore: 82,
    reason: "模拟数据：假设节日和国风穿搭带动新中式晕染需求上升。",
    targetUsers: ["追求社交平台出片用户", "节日场景用户"],
    suggestedStyles: ["新中式款式", "晕染款式", "钻饰点缀款式"],
    merchantActions: [
      "将新中式晕染设为节日主题专区主推款。",
      "配置 2-3 个复杂度档位，方便商家做价格分层。",
      "搭配手部照片模板，提升 AI 试戴转化。"
    ],
    recommendedPromotionCopy:
      "模拟文案：新中式晕染上手很适合拍照，先用 AI 试戴看看和你的肤色搭不搭。"
  },
  {
    keyword: "短甲纯色",
    title: "模拟趋势：短甲纯色高质感款",
    hotspotScore: 79,
    popularityScore: 74,
    relevanceScore: 90,
    growthScore: 68,
    noveltyScore: 64,
    merchantFeasibilityScore: 95,
    conversionPotentialScore: 78,
    reason: "模拟数据：假设短甲用户更关注耐看、好打理和快速交付。",
    targetUsers: ["通勤白领", "偏好快速换款用户"],
    suggestedStyles: ["短甲款式", "纯色款式", "裸色款式"],
    merchantActions: [
      "将短甲纯色放入快速预约专区。",
      "用基础款价格承接高频复购用户。",
      "减少复杂装饰，突出交付速度和耐看度。"
    ],
    recommendedPromotionCopy:
      "模拟文案：短甲也能很精致，纯色高质感款适合上班、通勤和日常拍照。"
  },
  {
    keyword: "多巴胺渐变",
    title: "模拟趋势：多巴胺渐变拍照款",
    hotspotScore: 75,
    popularityScore: 72,
    relevanceScore: 88,
    growthScore: 70,
    noveltyScore: 86,
    merchantFeasibilityScore: 72,
    conversionPotentialScore: 74,
    reason: "模拟数据：假设年轻用户对彩色渐变和社交平台出片需求增加。",
    targetUsers: ["追求社交平台出片用户"],
    suggestedStyles: ["多巴胺款式", "渐变款式", "ins风款式"],
    merchantActions: [
      "将多巴胺渐变放入拍照款专区。",
      "搭配不同肤色试戴图，降低用户选择成本。",
      "内容发布重点突出“上镜”“显手白”。"
    ],
    recommendedPromotionCopy:
      "模拟文案：多巴胺渐变适合想换心情的你，先试戴再决定哪组配色最显白。"
  },
  {
    keyword: "穿戴甲贴片",
    title: "模拟趋势：穿戴甲快速换款",
    hotspotScore: 72,
    popularityScore: 70,
    relevanceScore: 92,
    growthScore: 66,
    noveltyScore: 62,
    merchantFeasibilityScore: 94,
    conversionPotentialScore: 80,
    reason: "模拟数据：假设低门槛、快速换款需求推动穿戴甲咨询增长。",
    targetUsers: ["偏好快速换款用户", "节日场景用户"],
    suggestedStyles: ["穿戴甲款式", "贴片款式", "甲片款式"],
    merchantActions: [
      "将穿戴甲套装排到商品列表前列。",
      "同步展示库存颜色和可发货款式。",
      "AI 试戴入口增加贴片上手效果预览。"
    ],
    recommendedPromotionCopy:
      "模拟文案：想临时换造型？穿戴甲先试戴看效果，喜欢再下单更稳。"
  }
];

export function generateSimulatedManicureHotspotsReport(
  limit: number,
  fallbackReason: string,
  generatedAt = new Date()
): ManicureHotspotsData {
  const date = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).format(generatedAt);
  const topHotspots = SIMULATED_TRENDS.slice(0, limit);
  const topNames = topHotspots.map((hotspot) => hotspot.keyword);

  return {
    generatedAt: generatedAt.toISOString(),
    dataSource: "simulated",
    isSimulated: true,
    fallbackReason,
    summary: `模拟报告：因当前无法获取小红书真实 API 数据，本报告使用演示数据推演。假设近期美甲热点集中在 ${topNames.slice(0, 4).join("、")} 等方向，可用于展示“每日两份报告 + 自动调整展出顺序”的产品流程。`,
    topHotspots,
    dailyReport: {
      date,
      overview: `模拟数据识别到 ${topHotspots.length} 个美甲热点，用于演示商家运营日报结构。`,
      topTrendSummary: `模拟热门款式 TOP 榜：${topNames.join(" / ")}。`,
      risingTrends: topHotspots
        .slice(0, 3)
        .map((hotspot) => `${hotspot.keyword}：${hotspot.reason}`),
      lowAttentionWarnings: [
        "模拟数据不能直接作为真实采购依据。",
        "真实 API 恢复后，应以小红书真实热度和门店转化数据重新排序。"
      ],
      recommendedMainPushStyles: topHotspots
        .slice(0, 3)
        .map((hotspot) => `${hotspot.keyword}：模拟建议放入首页推荐位。`),
      pricingSuggestions: topHotspots
        .slice(0, 3)
        .map((hotspot) => `${hotspot.keyword} 可设置基础款、进阶款两档用于演示转化策略。`),
      contentSuggestions: topHotspots
        .slice(0, 3)
        .map((hotspot) => hotspot.recommendedPromotionCopy),
      inventorySuggestions: topHotspots
        .slice(0, 3)
        .map((hotspot) => `模拟检查 ${hotspot.keyword} 相关色胶、甲片和饰品库存。`)
    },
    intelligentExecution: {
      homepageRecommendationUpdates: topHotspots
        .slice(0, 3)
        .map(
          (hotspot, index) =>
            `模拟推荐位 ${index + 1} 更新为“${hotspot.keyword}”，真实 API 恢复后自动替换。`
        ),
      styleListAdjustments: topHotspots
        .slice(0, 3)
        .map((hotspot) => `模拟将“${hotspot.keyword}”相关商品上移至款式列表前排。`),
      contentPublishingPlan: topHotspots
        .slice(0, 3)
        .map((hotspot) => `模拟发布内容：${hotspot.recommendedPromotionCopy}`),
      aiTryOnStyleUpdates: topHotspots
        .slice(0, 3)
        .map((hotspot) => `模拟在 AI 试戴款式池置顶“${hotspot.keyword}”。`),
      merchantTodoList: [
        "上午报告：模拟更新首页推荐位和试戴入口。",
        "下午报告：模拟根据点击/咨询表现复核展出顺序。",
        "真实 API 恢复后，自动切回真实趋势数据并重新生成排序建议。"
      ]
    }
  };
}
