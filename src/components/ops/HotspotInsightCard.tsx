import { ExternalLink, Flame, Sparkles, Users } from "lucide-react";
import type { ManicureHotspotsData } from "@/types/manicureHotspots";

type Hotspot = ManicureHotspotsData["topHotspots"][number];

interface HotspotInsightCardProps {
  hotspot: Hotspot;
  index: number;
}

export function HotspotInsightCard({ hotspot, index }: HotspotInsightCardProps) {
  const sourceUrl = isHttpUrl(hotspot.sourceUrl) ? hotspot.sourceUrl : undefined;

  return (
    <article className="hotspot-card">
      <div className="hotspot-rank">TOP {index + 1}</div>
      <div className="hotspot-card-main">
        <div>
          <p className="source-pill">Xiaohongshu</p>
          <h3>{hotspot.keyword}</h3>
          <p className="hotspot-title">{hotspot.title}</p>
        </div>
        <div className="score-ring" aria-label={`热点分 ${hotspot.hotspotScore}`}>
          <strong>{hotspot.hotspotScore}</strong>
          <span>热点分</span>
        </div>
      </div>

      <div className="metric-grid">
        <Metric icon={<Flame size={15} />} label="热度" value={formatMetric(hotspot.heatScore, hotspot.popularityScore)} />
        <Metric icon={<Sparkles size={15} />} label="相关" value={`${hotspot.relevanceScore}`} />
        <Metric icon={<Users size={15} />} label="排名" value={hotspot.rank ? `#${hotspot.rank}` : "未提供"} />
      </div>

      <p className="reason">{hotspot.reason}</p>

      <div className="hotspot-sections">
        <InfoList title="建议款式" items={hotspot.suggestedStyles} />
        <InfoList title="目标用户" items={hotspot.targetUsers} emptyText="待结合门店客群判断" />
        <InfoList title="商家动作" items={hotspot.merchantActions} />
      </div>

      <div className="copy-strip">
        <span>推广文案</span>
        <p>{hotspot.recommendedPromotionCopy}</p>
      </div>

      {sourceUrl ? (
        <a className="source-link" href={sourceUrl} target="_blank" rel="noreferrer">
          查看趋势来源 <ExternalLink size={15} />
        </a>
      ) : null}
    </article>
  );
}

function Metric({
  icon,
  label,
  value
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="metric">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function InfoList({
  title,
  items,
  emptyText = "暂无"
}: {
  title: string;
  items: string[];
  emptyText?: string;
}) {
  return (
    <section>
      <h4>{title}</h4>
      <ul>
        {(items.length > 0 ? items : [emptyText]).map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function formatMetric(heatScore: number | undefined, popularityScore: number): string {
  if (typeof heatScore === "number") {
    return `${heatScore}`;
  }

  return `${popularityScore}`;
}

function isHttpUrl(value: string | undefined): value is string {
  return Boolean(value && /^https?:\/\//i.test(value));
}
