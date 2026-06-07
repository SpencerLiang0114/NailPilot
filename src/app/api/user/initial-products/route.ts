import { proxyJson } from "../backend";

export const dynamic = "force-dynamic";

export async function GET() {
  return proxyJson("/api/initial_products");
}
