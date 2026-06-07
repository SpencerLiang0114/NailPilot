const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";

export function getNailTryonBackendUrl() {
  return (process.env.NAIL_TRYON_API_BASE_URL ?? DEFAULT_BACKEND_URL).replace(/\/$/, "");
}

export function backendUrl(path: string) {
  return `${getNailTryonBackendUrl()}${path.startsWith("/") ? path : `/${path}`}`;
}

export function jsonError(message: string, status = 502) {
  return Response.json({ success: false, error: message }, { status });
}

export async function proxyJson(path: string, init?: RequestInit) {
  try {
    const response = await fetch(backendUrl(path), {
      ...init,
      cache: "no-store"
    });
    const body = await response.text();
    return new Response(body, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/json"
      }
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Backend request failed";
    return jsonError(message);
  }
}
