import Link from "next/link";
import type { ReactNode } from "react";

type PortalCardProps = {
  eyebrow: string;
  title: string;
  description: string;
  href: string;
  cta: string;
  icon: ReactNode;
};

export function PortalCard({
  eyebrow,
  title,
  description,
  href,
  cta,
  icon
}: PortalCardProps) {
  return (
    <article className="portal-card">
      <div className="portal-card-top">
        <div className="portal-card-icon" aria-hidden="true">
          {icon}
        </div>
        <Link className="portal-card-cta" href={href}>
          {cta}
        </Link>
      </div>
      <p className="portal-card-eyebrow">{eyebrow}</p>
      <h2>{title}</h2>
      <p>{description}</p>
    </article>
  );
}
