import type { Envelope } from "./types";

export class ApiError extends Error {}

export async function getJson<T>(path: string): Promise<Envelope<T>> {
  const response = await fetch(path, { credentials: "same-origin" });
  if (!response.ok) {
    if (response.status === 401) {
      window.dispatchEvent(new Event("crosslayer:unauthorized"));
    }
    throw new ApiError(`HTTP ${response.status} for ${path}`);
  }
  return (await response.json()) as Envelope<T>;
}
