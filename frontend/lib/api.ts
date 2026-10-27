/** Fetch wrapper for the FastAPI backend, reached through the `/api` rewrite in next.config.ts. */

export interface FieldProblem {
  field: string;
  message: string;
}

/** Mirrors the backend envelope: {"error": {"code", "message", ...extra}}. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly fields: FieldProblem[] = [],
    readonly extra: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }

  fieldMessage(field: string): string | undefined {
    return this.fields.find((f) => f.field === field)?.message;
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as {
      error?: { code?: string; message?: string; fields?: FieldProblem[] } & Record<string, unknown>;
    };
    const { code = "http_error", message = response.statusText, fields = [], ...extra } =
      body.error ?? {};
    return new ApiError(response.status, code, message, fields, extra);
  } catch {
    return new ApiError(response.status, "http_error", response.statusText || "Request failed");
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  let response: Response;
  try {
    response = await fetch(`/api${path}`, { ...init, headers, credentials: "same-origin" });
  } catch {
    throw new ApiError(0, "network_error", "Can't reach the server. Check your connection.");
  }
  if (!response.ok) {
    throw await toApiError(response);
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}

/** Errors worth showing inline; a 401 is handled by the session redirect instead. */
export function shownError(error: ApiError | undefined): ApiError | undefined {
  return error?.status === 401 ? undefined : error;
}

export function asApiError(error: unknown): ApiError {
  return error instanceof ApiError
    ? error
    : new ApiError(0, "unexpected_error", "Something went wrong. Try again.");
}
