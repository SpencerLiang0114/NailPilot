import Link from "next/link";

export default function UserPlaceholderPage() {
  return (
    <main className="placeholder-shell">
      <section className="placeholder-panel" aria-labelledby="user-placeholder-title">
        <p className="portal-badge">User Side</p>
        <h1 id="user-placeholder-title">User Side Coming Soon</h1>
        <p>
          This area is reserved for the user-facing Nail Art World Cup
          experience.
        </p>
        <Link className="portal-card-cta" href="/">
          Back to Portal
        </Link>
      </section>
    </main>
  );
}
