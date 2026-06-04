"use client";

import { useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  FileText,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Sparkles
} from "lucide-react";
import { HotspotInsightCard } from "@/components/ops/HotspotInsightCard";
import { IntelligentExecutionPanel } from "@/components/ops/IntelligentExecutionPanel";
import { OperationsDailyReport } from "@/components/ops/OperationsDailyReport";
import type { ManicureHotspotsApiResponse } from "@/types/manicureHotspots";

type DashboardState =
  | { status: "idle"; response?: undefined }
  | { status: "loading"; response?: undefined }
  | { status: "success"; response: ManicureHotspotsApiResponse }
  | { status: "error"; message: string };

export function ManicureHotspotDashboard() {
  const [keyword, setKeyword] = useState("美甲");
  const [state, setState] = useState<DashboardState>({ status: "idle" });

  const data =
    state.status === "success" && state.response.success
      ? state.response.data
      : undefined;
  const error =
    state.status === "success" && !state.response.success
      ? state.response.error
      : undefined;
  const generatedTime = useMemo(() => {
    if (!data) {
      return "等待生成";
    }

    return new Intl.DateTimeFormat("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
      month: "2-digit",
      day: "2-digit"
    }).format(new Date(data.generatedAt));
  }, [data]);

  async function generateReport(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState({ status: "loading" });

    const params = new URLSearchParams({ source: "xhs", limit: "5" });
    const trimmedKeyword = keyword.trim();
    if (trimmedKeyword) {
      params.set("keyword", trimmedKeyword);
    }

    try {
      const response = await fetch(`/api/ops/manicure-hotspots?${params}`, {
        cache: "no-store"
      });
      const json = (await response.json()) as ManicureHotspotsApiResponse;
      setState({ status: "success", response: json });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "请求运营日报失败。"
      });
    }
  }

  return (
    <main className="ops-shell">
      <section className="hero-band">
        <div className="hero-copy">
          <p className="eyebrow">AI Merchant Ops</p>
          <h1>美甲热点 Review</h1>
          <p className="subtitle">基于小红书实时趋势生成今日运营日报与款式调整建议</p>
        </div>

        <form className="keyword-form" onSubmit={generateReport}>
          <label htmlFor="keyword">关键词追踪</label>
          <div>
            <Search size={17} />
            <input
              id="keyword"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              placeholder="美甲 / 猫眼 / 穿戴甲"
            />
            <button type="submit" disabled={state.status === "loading"}>
              <ArrowRight size={17} />
              <span>{state.status === "loading" ? "生成中" : "生成报告"}</span>
            </button>
          </div>
        </form>
      </section>

      <section className="logic-strip" aria-label="operations workflow">
        <WorkflowCard
          icon={<Activity size={22} />}
          title="趋势洞察"
          description="识别小红书真实热搜与内容信号中的美甲相关趋势。"
        />
        <WorkflowCard
          icon={<FileText size={22} />}
          title="运营日报生成"
          description="按热度、相关性、增长和转化潜力生成今日美甲运营结论。"
        />
        <WorkflowCard
          icon={<SlidersHorizontal size={22} />}
          title="智能调整执行"
          description="输出首页推荐、款式列表、试戴入口和内容发布动作。"
        />
      </section>

      {state.status === "idle" ? <IdleState /> : null}

      {state.status === "loading" ? <LoadingState /> : null}

      {state.status === "error" ? <ErrorState message={state.message} /> : null}

      {error ? (
        <ErrorState
          title={
            error.code === "XHS_API_CONFIG_MISSING"
              ? "未读取到小红书 API Key，暂无法生成真实趋势报告。"
              : "小红书 API 请求失败"
          }
          message={error.message}
        />
      ) : null}

      {data ? (
        <section className="dashboard-grid">
          <article className="summary-panel">
            <div>
              <p>今日热点报告</p>
              <h2>{data.topHotspots.length > 0 ? "美甲热点 Review" : "暂无真实趋势数据"}</h2>
            </div>
            <p className="summary-text">
              {data.topHotspots.length > 0
                ? data.summary
                : "当前未识别到明确的美甲相关热点。"}
            </p>
            <div className="summary-meta">
              <span>来源：Xiaohongshu</span>
              <span>生成：{generatedTime}</span>
              <span>趋势数：{data.topHotspots.length}</span>
            </div>
          </article>

          {data.topHotspots.length > 0 ? (
            <section className="hotspot-list">
              {data.topHotspots.map((hotspot, index) => (
                <HotspotInsightCard
                  key={`${hotspot.keyword}-${hotspot.title}`}
                  hotspot={hotspot}
                  index={index}
                />
              ))}
            </section>
          ) : (
            <EmptyState />
          )}

          <OperationsDailyReport report={data.dailyReport} />
          <IntelligentExecutionPanel execution={data.intelligentExecution} />

          {data.topHotspots.length > 0 ? (
            <section className="promotion-panel">
              <div className="section-heading">
                <div>
                  <p>Promotion Copy</p>
                  <h2>推荐推广文案</h2>
                </div>
                <Sparkles size={21} />
              </div>
              <div className="copy-list">
                {data.topHotspots.slice(0, 3).map((hotspot) => (
                  <article key={`${hotspot.keyword}-copy`}>
                    <span>{hotspot.keyword}</span>
                    <p>{hotspot.recommendedPromotionCopy}</p>
                  </article>
                ))}
              </div>
            </section>
          ) : null}
        </section>
      ) : null}
    </main>
  );
}

function WorkflowCard({
  icon,
  title,
  description
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <article className="workflow-card">
      <div className="workflow-icon">{icon}</div>
      <h2>{title}</h2>
      <p>{description}</p>
    </article>
  );
}

function IdleState() {
  return (
    <section className="status-panel status-empty">
      <h2>点击“生成报告”后获取小红书真实趋势。</h2>
      <p>进入页面不会自动消耗接口调用；系统只会在你手动触发后生成今日热点 Review 与运营日报。</p>
    </section>
  );
}

function LoadingState() {
  return (
    <section className="status-panel">
      <RefreshCw size={22} className="spin" />
      <h2>正在获取小红书实时趋势...</h2>
      <p>系统会在接口返回后生成今日热点 Review 与运营日报。</p>
    </section>
  );
}

function ErrorState({
  title = "请求失败",
  message
}: {
  title?: string;
  message: string;
}) {
  return (
    <section className="status-panel status-error">
      <h2>{title}</h2>
      <p>{message}</p>
    </section>
  );
}

function EmptyState() {
  return (
    <section className="status-panel status-empty">
      <h2>当前未识别到明确的美甲相关热点。</h2>
      <p>页面未使用 mock 数据；请配置真实小红书热搜接口或扩大关键词查询范围。</p>
    </section>
  );
}
