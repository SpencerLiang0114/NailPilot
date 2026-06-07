import { Crown, Sparkles, Store, Trophy } from "lucide-react";
import { PortalCard } from "@/components/PortalCard";

export default function Home() {
  return (
    <main className="portal-shell">
      <nav className="portal-nav" aria-label="Primary">
        <div className="portal-brand">
          <span aria-hidden="true">
            <Crown size={18} />
          </span>
          Nail Art World Cup
        </div>
        <span className="portal-nav-note">美甲世界杯</span>
      </nav>

      <section className="portal-hero" aria-labelledby="portal-title">
        <div className="portal-hero-copy">
          <p className="portal-badge">Meituan Hackathon Project</p>
          <h1 id="portal-title">Nail Art World Cup</h1>
          <p>
            A creative platform for nail art discovery, competition, and
            merchant-side intelligent operations.
          </p>
        </div>

        <div className="portal-stage" aria-hidden="true">
          <div className="stage-medal">
            <Trophy size={42} />
          </div>
          <div className="stage-arc" />
          <div className="stage-nail stage-nail-primary" />
          <div className="stage-nail stage-nail-secondary" />
          <div className="stage-caption">World Cup</div>
        </div>
      </section>

      <section className="portal-entry-grid" aria-label="Platform entries">
        <PortalCard
          eyebrow="Consumer Experience"
          title="User Side"
          description="Discover trending nail styles, explore creative inspiration, and experience the consumer-facing Nail Art World Cup journey."
          href="/user"
          cta="Enter User Side"
          icon={<Sparkles size={28} />}
        />
        <PortalCard
          eyebrow="Merchant Operations"
          title="Merchant Side"
          description="Use hotspot generation, trend reports, and operation insights to help merchants capture nail art demand."
          href="/merchant"
          cta="Enter Merchant Side"
          icon={<Store size={28} />}
        />
      </section>
    </main>
  );
}
