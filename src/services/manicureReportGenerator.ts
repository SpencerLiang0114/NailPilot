import type {
  IntelligentExecution,
  ManicureHotspotsData,
  OperationsDailyReport,
  ScoredManicureHotspot
} from "@/types/manicureHotspots";

export function generateManicureHotspotsReport(
  hotspots: ScoredManicureHotspot[],
  generatedAt = new Date()
): ManicureHotspotsData {
  const date = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).format(generatedAt);

  const publicHotspots = hotspots.map(({ sourceTrend: _sourceTrend, ...hotspot }) => hotspot);

  return {
    generatedAt: generatedAt.toISOString(),
    dataSource: "xiaohongshu",
    summary: buildSummary(hotspots),
    topHotspots: publicHotspots,
    dailyReport: buildDailyReport(hotspots, date),
    intelligentExecution: buildIntelligentExecution(hotspots)
  };
}

function buildSummary(hotspots: ScoredManicureHotspot[]): string {
  if (hotspots.length === 0) {
    return "当前小红书热搜中暂未识别到足够明确的美甲相关趋势。";
  }

  const topTerms = hotspots
    .slice(0, 4)
    .map((hotspot) => hotspot.keyword)
    .join("、");

  return `今日美甲趋势集中在 ${topTerms} 等方向。建议将高热度款式放入首页推荐位，并同步更新 AI 试戴入口。`;
}

function buildDailyReport(
  hotspots: ScoredManicureHotspot[],
  date: string
): OperationsDailyReport {
  if (hotspots.length === 0) {
    return {
      date,
      overview: "暂无可用于生成运营结论的真实美甲趋势数据。",
      topTrendSummary: "当前未识别到明确的美甲相关热点。",
      risingTrends: [],
      lowAttentionWarnings: ["未接入店铺款式曝光/预约转化数据，暂不判断低关注款式。"],
      recommendedMainPushStyles: [],
      pricingSuggestions: [],
      contentSuggestions: [],
      inventorySuggestions: []
    };
  }

  const topNames = hotspots.slice(0, 5).map((hotspot) => hotspot.keyword);
  const risingTrends = hotspots
    .filter((hotspot) => hotspot.growthScore > 0)
    .slice(0, 3)
    .map((hotspot) => `${hotspot.keyword}：${hotspot.reason}`);

  return {
    date,
    overview: `今日识别到 ${hotspots.length} 个美甲相关小红书趋势，TOP 款式为 ${topNames.slice(0, 3).join("、")}。`,
    topTrendSummary: `热门款式 TOP 榜：${topNames.join(" / ")}。`,
    risingTrends:
      risingTrends.length > 0
        ? risingTrends
        : ["真实接口未提供明确增长字段，当前按热度、互动和发布时间辅助判断。"],
    lowAttentionWarnings: [
      "未接入店铺款式曝光/预约转化数据，暂不移除低关注款式。",
      "缺少平台增长字段的趋势不应单独作为采购依据，需要结合门店预约数据复核。"
    ],
    recommendedMainPushStyles: hotspots
      .slice(0, 3)
      .map((hotspot) => `${hotspot.keyword}：优先放入首页推荐和到店咨询话术。`),
    pricingSuggestions: hotspots
      .slice(0, 3)
      .map((hotspot) => `${hotspot.keyword} 可设置基础款与进阶款两档，避免只推高价复杂款。`),
    contentSuggestions: hotspots
      .slice(0, 3)
      .map((hotspot) => hotspot.recommendedPromotionCopy),
    inventorySuggestions: hotspots
      .slice(0, 3)
      .map((hotspot) => `检查 ${hotspot.keyword} 相关甲片、色胶、饰品和样板库存。`)
  };
}

function buildIntelligentExecution(
  hotspots: ScoredManicureHotspot[]
): IntelligentExecution {
  if (hotspots.length === 0) {
    return {
      homepageRecommendationUpdates: [],
      styleListAdjustments: [],
      contentPublishingPlan: [],
      aiTryOnStyleUpdates: [],
      merchantTodoList: ["配置小红书 API 并重新生成今日运营日报。"]
    };
  }

  const top = hotspots.slice(0, 3);

  return {
    homepageRecommendationUpdates: top.map(
      (hotspot, index) => `推荐位 ${index + 1} 更新为“${hotspot.keyword}”，展示来源热度和试戴入口。`
    ),
    styleListAdjustments: top.map(
      (hotspot) => `将“${hotspot.keyword}”相关款式上移至列表前排，保留来源链接供运营复核。`
    ),
    contentPublishingPlan: top.map(
      (hotspot) => `围绕“${hotspot.keyword}”发布一篇种草内容：${hotspot.recommendedPromotionCopy}`
    ),
    aiTryOnStyleUpdates: top.map(
      (hotspot) => `在 AI 试戴款式池中新增或置顶“${hotspot.keyword}”近似款。`
    ),
    merchantTodoList: [
      "复核 TOP 款式是否有可交付样板图和技师操作 SOP。",
      "将小红书热词同步到门店私域文案和团购标题。",
      "明日对比预约点击、收藏咨询和到店转化，判断是否继续主推。"
    ]
  };
}
