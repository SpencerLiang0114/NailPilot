import { AlertTriangle, BarChart3, CalendarDays, Megaphone } from "lucide-react";
import type { OperationsDailyReport as OperationsDailyReportType } from "@/types/manicureHotspots";

interface OperationsDailyReportProps {
  report: OperationsDailyReportType;
}

export function OperationsDailyReport({ report }: OperationsDailyReportProps) {
  return (
    <section className="report-panel">
      <div className="section-heading">
        <div>
          <p>Daily Report</p>
          <h2>运营日报</h2>
        </div>
        <span className="report-date">
          <CalendarDays size={16} />
          {report.date}
        </span>
      </div>

      <div className="report-overview">
        <BarChart3 size={18} />
        <p>{report.overview}</p>
      </div>

      <div className="report-grid">
        <ReportBlock title="热门款式 TOP 榜" items={[report.topTrendSummary]} />
        <ReportBlock title="今日运营建议" items={report.recommendedMainPushStyles} />
        <ReportBlock title="内容发布建议" items={report.contentSuggestions} icon={<Megaphone size={16} />} />
        <ReportBlock title="风险提示" items={report.lowAttentionWarnings} icon={<AlertTriangle size={16} />} />
        <ReportBlock title="定价建议" items={report.pricingSuggestions} />
        <ReportBlock title="库存建议" items={report.inventorySuggestions} />
      </div>
    </section>
  );
}

function ReportBlock({
  title,
  items,
  icon
}: {
  title: string;
  items: string[];
  icon?: React.ReactNode;
}) {
  return (
    <article className="report-block">
      <h3>
        {icon}
        {title}
      </h3>
      <ul>
        {(items.length > 0 ? items : ["暂无真实数据支持的建议。"]).map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </article>
  );
}
