import { useEffect, useState } from "react";
import { getJson } from "../api/client";
import type { Envelope } from "../api/types";

export function usePoll<T>(path: string, intervalMs = 15000) {
  const [data, setData] = useState<Envelope<T> | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const body = await getJson<T>(path);
        if (!cancelled) {
          setData(body);
          setLoadError(null);
        }
      } catch (err) {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : "request failed");
      }
    }
    load();
    const id = setInterval(load, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [path, intervalMs]);

  return { data, loadError };
}
