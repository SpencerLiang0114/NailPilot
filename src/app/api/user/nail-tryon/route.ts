import { backendUrl, jsonError } from "../backend";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

export async function POST(request: Request) {
  let formData: FormData;

  try {
    formData = await request.formData();
  } catch {
    return jsonError("Invalid upload payload.", 400);
  }

  try {
    const response = await fetch(backendUrl("/api/nail_tryon"), {
      method: "POST",
      body: formData,
      cache: "no-store"
    });

    const contentType = response.headers.get("content-type") ?? "application/octet-stream";
    const body = await response.arrayBuffer();

    return new Response(body, {
      status: response.status,
      headers: {
        "content-type": contentType
      }
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Try-on backend request failed";
    return jsonError(message);
  }
}
