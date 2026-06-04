import { CheckCircle2, Cpu, Layers3, ListChecks, WandSparkles } from "lucide-react";
import type { IntelligentExecution } from "@/types/manicureHotspots";

interface IntelligentExecutionPanelProps {
  execution: IntelligentExecution;
}

export function IntelligentExecutionPanel({
  execution
}: IntelligentExecutionPanelProps) {
  return (
    <section className="execution-panel">
      <div className="section-heading">
        <div>
          <p>Execution</p>
          <h2>智能调整执行</h2>
        </div>
        <Cpu size={22} />
      </div>

      <div className="execution-grid">
        <ExecutionColumn
          icon={<Layers3 size={17} />}
          title="首页推荐位"
          items={execution.homepageRecommendationUpdates}
        />
        <ExecutionColumn
          icon={<WandSparkles size={17} />}
          title="AI 试戴款式"
          items={execution.aiTryOnStyleUpdates}
        />
        <ExecutionColumn
          icon={<ListChecks size={17} />}
          title="款式列表调整"
          items={execution.styleListAdjustments}
        />
        <ExecutionColumn
          icon={<CheckCircle2 size={17} />}
          title="今日待办"
          items={execution.merchantTodoList}
        />
      </div>
    </section>
  );
}

function ExecutionColumn({
  icon,
  title,
  items
}: {
  icon: React.ReactNode;
  title: string;
  items: string[];
}) {
  return (
    <article className="execution-column">
      <h3>
        {icon}
        {title}
      </h3>
      <ol>
        {(items.length > 0 ? items : ["暂无可执行建议。"]).map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ol>
    </article>
  );
}
