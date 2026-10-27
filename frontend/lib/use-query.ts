"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, asApiError } from "./api";

interface QueryState<T> {
  key?: string;
  data?: T;
  error?: ApiError;
}

export interface Query<T> {
  data: T | undefined;
  error: ApiError | undefined;
  /** True until the first response for the current key arrives. */
  loading: boolean;
  reload: () => void;
}

/**
 * Loads data for `key` and reloads when it changes. Previous data stays visible while a new
 * key loads, so paging and filtering don't flash an empty state.
 */
export function useQuery<T>(
  key: string | null,
  load: () => Promise<T>,
  options: { pollWhile?: (data: T | undefined) => boolean; pollMs?: number } = {},
): Query<T> {
  const [state, setState] = useState<QueryState<T>>({});
  const [nonce, setNonce] = useState(0);
  const loadRef = useRef(load);

  useEffect(() => {
    loadRef.current = load;
  });

  useEffect(() => {
    if (key === null) return;
    let cancelled = false;
    loadRef.current().then(
      (data) => !cancelled && setState({ key, data }),
      (error: unknown) => !cancelled && setState((prev) => ({ ...prev, key, error: asApiError(error) })),
    );
    return () => {
      cancelled = true;
    };
  }, [key, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  const { pollWhile, pollMs = 1000 } = options;
  const shouldPoll = pollWhile ? pollWhile(state.data) : false;
  useEffect(() => {
    if (!shouldPoll) return;
    const timer = setInterval(reload, pollMs);
    return () => clearInterval(timer);
  }, [shouldPoll, pollMs, reload]);

  return {
    data: state.data,
    error: state.key === key ? state.error : undefined,
    loading: state.key !== key,
    reload,
  };
}
