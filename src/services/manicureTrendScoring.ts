import type {
  NormalizedXhsTrend,
  ScoredManicureHotspot
} from "@/types/manicureHotspots";
import {
  type RelevanceResult,
  extractMatchedStyleTerms
} from "@/services/manicureTrendFilter";

type JsonRecord = Record<string, unknown>;

const SEASONAL_OR_FRESH_TERMS = [
  "圣诞",
  "新年",
  "秋冬",
  "节日",
  "婚礼",
  "新中式",
  "多巴胺",
  "甜酷",
  "猫眼",
  "腮红甲",
  "晕染",
  "渐变",
  "ins风"
];

const FEASIBLE_TERMS = ["纯色", "裸色", "法式", "短甲", "猫眼", "贴片", "甲片", "穿戴甲", "显白"];
const CONVERSION_TERMS = ["显白", "通勤", "婚礼", "节日", "约会", "上班", "穿戴甲", "甲片", "短甲"];

export function scoreManicureHotspots(
  relevanceResults: RelevanceResult[],
  limit: number
): ScoredManicureHotspot[] {
  return relevanceResults
    .map(({ trend, relevanceScore, matchedTerms }) =>
      buildScoredHotspot(trend, relevanceScore, matchedTerms)
    )
    .sort((a, b) => b.hotspotScore - a.hotspotScore)
    .slice(0, limit);
}

function buildScoredHotspot(
  trend: NormalizedXhsTrend,
  relevanceScore: number,
  matchedTerms: string[]
): ScoredManicureHotspot {
  const text = `${trend.keyword} ${trend.title} ${trend.description ?? ""} ${trend.tags.join(" ")}`;
  const styleTerms = extractMatchedStyleTerms(text);
  const popularityScore = scorePopularity(trend);
  const growthScore = scoreGrowth(trend);
  const noveltyScore = scoreTermSignals(text, SEASONAL_OR_FRESH_TERMS, 70);
  const merchantFeasibilityScore = scoreTermSignals(text, FEASIBLE_TERMS, 65);
  const conversionPotentialScore = scoreTermSignals(text, CONVERSION_TERMS, 65);

  const hotspotScore = roundScore(
    popularityScore * 0.35 +
      relevanceScore * 0.25 +
      growthScore * 0.15 +
      noveltyScore * 0.1 +
      merchantFeasibilityScore * 0.1 +
      conversionPotentialScore * 0.05
  );

  return {
    keyword: trend.keyword,
    title: trend.title,
    hotspotScore,
    popularityScore,
    relevanceScore,
    growthScore,
    noveltyScore,
    merchantFeasibilityScore,
    conversionPotentialScore,
    reason: buildReason(trend, matchedTerms, {
      popularityScore,
      growthScore,
      noveltyScore
    }),
    targetUsers: inferTargetUsers(text),
    suggestedStyles: buildSuggestedStyles(styleTerms, trend.keyword),
    merchantActions: buildMerchantActions(styleTerms, trend),
    recommendedPromotionCopy: buildPromotionCopy(trend, styleTerms),
    sourceUrl: trend.sourceUrl,
    imageUrls: trend.imageUrls,
    rank: trend.rank,
    heatScore: trend.heatScore,
    sourceTrend: trend
  };
}

function scorePopularity(trend: NormalizedXhsTrend): number {
  const availableScores: number[] = [];

  if (typeof trend.heatScore === "number") {
    availableScores.push(normalizeLargeMetric(trend.heatScore));
  }

  if (typeof trend.rank === "number" && trend.rank > 0) {
    availableScores.push(Math.max(0, 100 - (trend.rank - 1) * 2.5));
  }

  const engagement =
    (trend.likeCount ?? 0) +
    (trend.collectCount ?? 0) * 1.2 +
    (trend.commentCount ?? 0) * 1.5 +
    (trend.shareCount ?? 0) * 1.8;

  if (engagement > 0) {
    availableScores.push(normalizeLargeMetric(engagement));
  }

  if (availableScores.length === 0) {
    return 0;
  }

  return roundScore(
    availableScores.reduce((sum, score) => sum + score, 0) / availableScores.length
  );
}

function scoreGrowth(trend: NormalizedXhsTrend): number {
  const raw = asRecord(trend.raw);
  const directGrowth = raw
    ? firstNumber(raw, [
        "growthScore",
        "growth_score",
        "growthRate",
        "growth_rate",
        "riseRate",
        "rise_rate"
      ])
    : undefined;

  if (typeof directGrowth === "number") {
    return roundScore(Math.max(0, Math.min(100, directGrowth)));
  }

  const rankChange = raw
    ? firstNumber(raw, ["rankChange", "rank_change", "rankDelta", "rank_delta"])
    : undefined;

  if (typeof rankChange === "number") {
    return roundScore(Math.max(0, Math.min(100, 50 + rankChange * 5)));
  }

  if (trend.publishTime) {
    const publishedAt = Date.parse(trend.publishTime);
    if (!Number.isNaN(publishedAt)) {
      const ageHours = (Date.now() - publishedAt) / 3_600_000;
      const engagement =
        (trend.likeCount ?? 0) +
        (trend.collectCount ?? 0) +
        (trend.commentCount ?? 0) +
        (trend.shareCount ?? 0);

      if (ageHours >= 0 && ageHours <= 72 && engagement > 0) {
        return roundScore(Math.min(100, 40 + normalizeLargeMetric(engagement) * 0.6));
      }
    }
  }

  return 0;
}

function scoreTermSignals(text: string, terms: string[], baseScore: number): number {
  const normalized = normalize(text);
  const hits = terms.filter((term) => normalized.includes(normalize(term))).length;

  if (hits === 0) {
    return 0;
  }

  return roundScore(Math.min(100, baseScore + hits * 8));
}

function buildReason(
  trend: NormalizedXhsTrend,
  matchedTerms: string[],
  scores: {
    popularityScore: number;
    growthScore: number;
    noveltyScore: number;
  }
): string {
  const signals = [
    trend.rank ? `热榜排名第 ${trend.rank}` : "",
    trend.heatScore ? `平台热度 ${trend.heatScore}` : "",
    matchedTerms.length ? `命中美甲词：${matchedTerms.slice(0, 4).join("、")}` : "",
    scores.growthScore > 0 ? "具备近期增长信号" : "未获得明确增长字段",
    scores.noveltyScore > 0 ? "包含季节或视觉风格信号" : ""
  ].filter(Boolean);

  return signals.length
    ? signals.join("；")
    : "该趋势来自真实小红书接口，但可用热度字段较少，仅按相关性进入候选。";
}

function inferTargetUsers(text: string): string[] {
  const normalized = normalize(text);
  const users = new Set<string>();

  if (["通勤", "上班", "裸色", "短甲"].some((term) => normalized.includes(term))) {
    users.add("通勤白领");
  }
  if (["婚礼", "约会", "法式", "钻饰"].some((term) => normalized.includes(term))) {
    users.add("约会/婚礼场景用户");
  }
  if (["穿戴甲", "甲片", "贴片"].some((term) => normalized.includes(term))) {
    users.add("偏好快速换款用户");
  }
  if (["甜酷", "多巴胺", "ins风", "新中式"].some((term) => normalized.includes(term))) {
    users.add("追求社交平台出片用户");
  }

  return Array.from(users).slice(0, 3);
}

function buildSuggestedStyles(styleTerms: string[], keyword: string): string[] {
  const suggestions = styleTerms.length > 0 ? styleTerms : [keyword];

  return suggestions.slice(0, 5).map((style) => `${style}款式`);
}

function buildMerchantActions(
  styleTerms: string[],
  trend: NormalizedXhsTrend
): string[] {
  const leadingStyle = styleTerms[0] || trend.keyword;

  return [
    `将“${leadingStyle}”加入今日首页推荐位。`,
    `同步更新 AI 试戴入口，优先展示与“${leadingStyle}”相近的款式。`,
    `围绕“${trend.keyword}”生成小红书风格标题，引导用户点击试戴和预约。`
  ];
}

function buildPromotionCopy(
  trend: NormalizedXhsTrend,
  styleTerms: string[]
): string {
  const leadingStyle = styleTerms[0] || trend.keyword;

  return `今天想换一款${leadingStyle}？参考小红书热度趋势，先用 AI 试戴看上手效果，再预约到店精修。`;
}

function normalizeLargeMetric(value: number): number {
  if (value <= 0) {
    return 0;
  }

  return roundScore(Math.min(100, (Math.log10(value + 1) / 6) * 100));
}

function roundScore(value: number): number {
  return Math.round(value * 10) / 10;
}

function firstNumber(record: JsonRecord, keys: string[]): number | undefined {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === "string") {
      const parsed = Number(value.replace(/[,%\s]/g, ""));
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
  }

  return undefined;
}

function asRecord(value: unknown): JsonRecord | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonRecord)
    : null;
}

function normalize(value: string): string {
  return value.toLowerCase().replace(/\s+/g, "");
}
