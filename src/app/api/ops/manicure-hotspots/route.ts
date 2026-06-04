import { NextRequest, NextResponse } from "next/server";
import { filterManicureTrends } from "@/services/manicureTrendFilter";
import { generateManicureHotspotsReport } from "@/services/manicureReportGenerator";
import { scoreManicureHotspots } from "@/services/manicureTrendScoring";
import { generateSimulatedManicureHotspotsReport } from "@/services/simulatedManicureReport";
import {
  XhsApiRequestError,
  fetchXhsHotTrends,
  fetchXhsKeywordTrends
} from "@/services/xiaohongshuTrendService";
import type {
  ManicureHotspotsApiResponse,
  NormalizedXhsTrend
} from "@/types/manicureHotspots";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const source = searchParams.get("source") ?? "xhs";
  const keyword = searchParams.get("keyword")?.trim();
  const limit = clampLimit(searchParams.get("limit"));

  if (source !== "xhs") {
    return NextResponse.json<ManicureHotspotsApiResponse>(
      {
        success: false,
        error: {
          code: "UNSUPPORTED_SOURCE",
          message: "Only source=xhs is supported for manicure hotspot review."
        }
      },
      { status: 400 }
    );
  }

  try {
    const [hotTrends, keywordTrends] = await Promise.all([
      fetchXhsHotTrends(),
      keyword ? fetchXhsKeywordTrends(keyword) : Promise.resolve([])
    ]);
    const manicureTrends = filterManicureTrends(
      dedupeTrends([...hotTrends, ...keywordTrends])
    );
    const scoredHotspots = scoreManicureHotspots(manicureTrends, limit);
    const data = generateManicureHotspotsReport(scoredHotspots);

    return NextResponse.json<ManicureHotspotsApiResponse>({
      success: true,
      data
    });
  } catch (error) {
    const message =
      error instanceof XhsApiRequestError || error instanceof Error
        ? error.message
        : "Unknown Xiaohongshu API error.";
    const data = generateSimulatedManicureHotspotsReport(limit, message);

    return NextResponse.json<ManicureHotspotsApiResponse>({
      success: true,
      data
    });
  }
}

function clampLimit(value: string | null): number {
  const parsed = Number(value);

  if (!Number.isFinite(parsed)) {
    return 5;
  }

  return Math.max(1, Math.min(20, Math.floor(parsed)));
}

function dedupeTrends(trends: NormalizedXhsTrend[]): NormalizedXhsTrend[] {
  const seen = new Set<string>();

  return trends.filter((trend) => {
    const key = `${trend.id}:${trend.title}:${trend.keyword}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}
