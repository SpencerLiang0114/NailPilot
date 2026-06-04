export type XhsTrendSource = "xiaohongshu";

export interface NormalizedXhsTrend {
  id: string;
  keyword: string;
  title: string;
  description?: string;
  heatScore?: number;
  rank?: number;
  sourceUrl?: string;
  tags: string[];
  imageUrls?: string[];
  publishTime?: string;
  likeCount?: number;
  collectCount?: number;
  commentCount?: number;
  shareCount?: number;
  raw: unknown;
}

export interface ScoredManicureHotspot {
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
  sourceUrl?: string;
  imageUrls?: string[];
  rank?: number;
  heatScore?: number;
  sourceTrend: NormalizedXhsTrend;
}

export interface OperationsDailyReport {
  date: string;
  overview: string;
  topTrendSummary: string;
  risingTrends: string[];
  lowAttentionWarnings: string[];
  recommendedMainPushStyles: string[];
  pricingSuggestions: string[];
  contentSuggestions: string[];
  inventorySuggestions: string[];
}

export interface IntelligentExecution {
  homepageRecommendationUpdates: string[];
  styleListAdjustments: string[];
  contentPublishingPlan: string[];
  aiTryOnStyleUpdates: string[];
  merchantTodoList: string[];
}

export interface ManicureHotspotsData {
  generatedAt: string;
  dataSource: XhsTrendSource;
  summary: string;
  topHotspots: Omit<ScoredManicureHotspot, "sourceTrend">[];
  dailyReport: OperationsDailyReport;
  intelligentExecution: IntelligentExecution;
}

export interface ManicureHotspotsSuccessResponse {
  success: true;
  data: ManicureHotspotsData;
}

export interface ManicureHotspotsErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
  };
}

export type ManicureHotspotsApiResponse =
  | ManicureHotspotsSuccessResponse
  | ManicureHotspotsErrorResponse;
