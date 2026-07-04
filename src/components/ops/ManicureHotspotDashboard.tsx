"use client";

import { useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  FileText,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Sparkles
} from "lucide-react";
import type {
  ManicureHotspotsApiResponse,
  ManicureHotspotsData
} from "@/types/manicureHotspots";

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
          {data.topHotspots.length > 0 ? (
            <ReportPoster data={data} generatedTime={generatedTime} />
          ) : (
            <EmptyState />
          )}
        </section>
      ) : null}
    </main>
  );
}

function ReportPoster({
  data,
  generatedTime
}: {
  data: ManicureHotspotsData;
  generatedTime: string;
}) {
  const topHotspots = data.topHotspots.slice(0, 5);
  const sourceLabel = data.isSimulated ? "模拟数据" : "小红书数据源";
  const topStyles = Array.from(
    new Set(topHotspots.flatMap((hotspot) => hotspot.suggestedStyles))
  ).slice(0, 6);
  const maxScore = Math.max(
    1,
    ...topHotspots.map((hotspot) => hotspot.hotspotScore)
  );

  return (
    <article className="report-poster" aria-label="美甲运营报告图">
      <header className="poster-header">
        <div>
          <p className="eyebrow">运营端 — AI助手智能运营</p>
          <h2>{data.isSimulated ? "美甲热点 Review 模拟日报" : "美甲热点 Review 日报"}</h2>
        </div>
        <div className="poster-meta">
          <span>
            <CalendarDays size={15} />
            {generatedTime}
          </span>
          <span>数据源：{sourceLabel}</span>
        </div>
      </header>

      {data.isSimulated ? (
        <section className="simulation-banner">
          <strong>当前为模拟报告</strong>
          <p>
            真实小红书 API 暂不可用，系统仅用模拟数据展示报告格式和自动排序逻辑。
            {data.fallbackReason ? ` 原因：${data.fallbackReason}` : ""}
          </p>
        </section>
      ) : null}

      <section className="poster-brief">
        <ul>
          <li>自动识别爆款趋势，按真实热度、相关性和可转化信号生成运营日报。</li>
          <li>每日建议产出两份报告：上午用于上新排序，下午用于复核展出顺序。</li>
          <li>输出可执行的商品置顶、AI 试戴款式池和内容发布建议。</li>
        </ul>
      </section>

      <section className="poster-main">
        <div className="poster-chart-card">
          <div className="poster-card-title">
            <BarChart3 size={18} />
            <h3>趋势图</h3>
          </div>
          <div className="trend-chart" role="img" aria-label="今日美甲热点分趋势图">
            {topHotspots.map((hotspot, index) => {
              const height = Math.max(18, (hotspot.hotspotScore / maxScore) * 100);

              return (
                <div className="trend-bar-column" key={`${hotspot.keyword}-bar`}>
                  <span>{Math.round(hotspot.hotspotScore)}</span>
                  <div
                    className="trend-bar"
                    style={{ height: `${height}%` }}
                    title={`${hotspot.keyword}：${hotspot.hotspotScore}`}
                  />
                  <p>{index + 1}</p>
                </div>
              );
            })}
          </div>
          <div className="trend-axis">
            {topHotspots.map((hotspot, index) => (
              <span key={`${hotspot.keyword}-axis`}>
                {index + 1}. {hotspot.keyword}
              </span>
            ))}
          </div>
        </div>

        <div className="poster-summary-card">
          <div className="poster-card-title">
            <Sparkles size={18} />
            <h3>当天热点总结</h3>
          </div>
          <p>{data.summary}</p>
          <div className="hot-style-cloud">
            {topStyles.map((style) => (
              <span key={style}>{style}</span>
            ))}
          </div>
          <div className="top-hotspot-line">
            <strong>最近爆火款式</strong>
            <p>{topHotspots.map((hotspot) => hotspot.keyword).join(" / ")}</p>
          </div>
        </div>
      </section>

      <section className="poster-flow">
        <PosterStep
          title="趋势洞察"
          items={topHotspots
            .slice(0, 3)
            .map(
              (hotspot) =>
                `${hotspot.keyword}：热点分 ${hotspot.hotspotScore}，${hotspot.reason}`
            )}
        />
        <div className="poster-arrow">→</div>
        <PosterStep
          title="运营日报生成"
          items={[
            data.dailyReport.overview,
            data.dailyReport.topTrendSummary,
            ...data.dailyReport.contentSuggestions.slice(0, 1)
          ]}
        />
        <div className="poster-arrow">→</div>
        <PosterStep
          title="智能调整执行"
          items={[
            ...data.intelligentExecution.homepageRecommendationUpdates.slice(0, 2),
            ...data.intelligentExecution.styleListAdjustments.slice(0, 1)
          ]}
        />
      </section>

      <section className="poster-bottom">
        <div>
          <h3>每日两份报告建议</h3>
          <ol>
            <li>上午 10:00：根据最新热点更新首页推荐位和 AI 试戴入口。</li>
            <li>下午 16:00：复核点击/咨询表现，调整商品展出顺序。</li>
          </ol>
        </div>
        <div>
          <h3>商品排序动作</h3>
          <ol>
            {data.intelligentExecution.merchantTodoList.slice(0, 3).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ol>
        </div>
      </section>

      <footer className="poster-footer">
        <CheckCircle2 size={18} />
        <span>
          {data.isSimulated
            ? "模拟报告仅用于演示；真实 API 恢复后会自动切回真实小红书数据。"
            : "报告基于真实接口返回数据生成；无数据或接口失败时不伪装为真实热点。"}
        </span>
      </footer>
    </article>
  );
}

function PosterStep({ title, items }: { title: string; items: string[] }) {
  return (
    <article className="poster-step">
      <h3>{title}</h3>
      <ul>
        {items.slice(0, 4).map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </article>
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
