import type {NextRequest} from "next/server";

type RouteContext = {
  params: Promise<{path: string[]}>;
};

async function proxy(request: NextRequest, context: RouteContext): Promise<Response> {
  const backendUrl = process.env.LOCAL_BACKEND_URL;
  const backendToken = process.env.LOCAL_BACKEND_TOKEN;
  if (!backendUrl || !backendToken) {
    return Response.json(
      {detail: "로컬 backend 연결 환경변수가 설정되지 않았습니다."},
      {status: 503},
    );
  }

  const {path} = await context.params;
  const encodedPath = path.map(encodeURIComponent).join("/");
  const target = new URL(`/${encodedPath}${request.nextUrl.search}`, backendUrl);
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  headers.set("x-local-api-token", backendToken);
  headers.set("ngrok-skip-browser-warning", "bookscript");

  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD"
        ? undefined
        : await request.arrayBuffer(),
      cache: "no-store",
    });
    const responseHeaders = new Headers();
    for (const name of ["content-type", "content-disposition"]) {
      const value = upstream.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch {
    return Response.json(
      {detail: "로컬 backend에 연결할 수 없습니다. 로컬 서비스를 확인해 주세요."},
      {status: 503},
    );
  }
}

export const dynamic = "force-dynamic";

export function GET(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export function POST(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}
