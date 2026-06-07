import { proxyJson } from "../backend";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const body = await request.text();
  return proxyJson("/recommendations", {
    method: "POST",
    headers: {
      "content-type": "application/json"
    },
    body
  });
}
