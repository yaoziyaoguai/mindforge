export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(await errorText(response));
  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await errorText(response));
  return response.json() as Promise<T>;
}

export async function apiPatch<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: "PATCH",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await errorText(response));
  return response.json() as Promise<T>;
}

export async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    method: "DELETE",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(await errorText(response));
  return response.json() as Promise<T>;
}

async function errorText(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string") return payload.detail;
    return payload?.detail?.message ?? payload?.message ?? response.statusText;
  } catch {
    return response.statusText;
  }
}
