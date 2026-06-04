import type { NormalizedXhsTrend } from "@/types/manicureHotspots";

export const MANICURE_KEYWORDS = [
  "美甲",
  "甲片",
  "穿戴甲",
  "光疗甲",
  "猫眼",
  "法式",
  "裸色",
  "显白",
  "甲油",
  "指甲",
  "新中式",
  "腮红甲",
  "短甲",
  "长甲",
  "手部",
  "贴片",
  "款式",
  "晕染",
  "渐变",
  "钻饰",
  "纯色",
  "ins风",
  "甜酷",
  "多巴胺",
  "秋冬美甲",
  "圣诞美甲",
  "婚礼美甲"
];

const IMAGE_CATEGORY_TERMS = ["nail", "manicure", "指甲", "美甲", "甲片"];

export interface RelevanceResult {
  trend: NormalizedXhsTrend;
  relevanceScore: number;
  matchedTerms: string[];
}

export function filterManicureTrends(
  trends: NormalizedXhsTrend[]
): RelevanceResult[] {
  return trends
    .map((trend) => ({
      trend,
      ...scoreManicureRelevance(trend)
    }))
    .filter((result) => result.relevanceScore >= 35);
}

export function scoreManicureRelevance(trend: NormalizedXhsTrend): {
  relevanceScore: number;
  matchedTerms: string[];
} {
  const keywordText = normalize(trend.keyword);
  const titleDescriptionText = normalize(`${trend.title} ${trend.description ?? ""}`);
  const tagsText = normalize(trend.tags.join(" "));
  const rawText = normalize(JSON.stringify(trend.raw));
  const matchedTerms = MANICURE_KEYWORDS.filter((term) => {
    const normalizedTerm = normalize(term);
    return (
      keywordText.includes(normalizedTerm) ||
      titleDescriptionText.includes(normalizedTerm) ||
      tagsText.includes(normalizedTerm)
    );
  });

  let score = 0;
  if (MANICURE_KEYWORDS.some((term) => keywordText.includes(normalize(term)))) {
    score += 45;
  }
  if (
    MANICURE_KEYWORDS.some((term) =>
      titleDescriptionText.includes(normalize(term))
    )
  ) {
    score += 30;
  }
  if (MANICURE_KEYWORDS.some((term) => tagsText.includes(normalize(term)))) {
    score += 20;
  }
  if (IMAGE_CATEGORY_TERMS.some((term) => rawText.includes(normalize(term)))) {
    score += 10;
  }

  return {
    relevanceScore: Math.min(100, score),
    matchedTerms
  };
}

export function extractMatchedStyleTerms(text: string): string[] {
  const normalizedText = normalize(text);

  return MANICURE_KEYWORDS.filter((term) =>
    normalizedText.includes(normalize(term))
  );
}

function normalize(value: string): string {
  return value.toLowerCase().replace(/\s+/g, "");
}
