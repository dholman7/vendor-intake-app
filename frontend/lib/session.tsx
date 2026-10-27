"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, type ReactNode } from "react";

import { api } from "./api";
import type { User } from "./types";
import { useQuery } from "./use-query";

interface Session {
  /** Null until /api/me answers. Pages load their own data in parallel and don't wait on it. */
  user: User | null;
  canReview: boolean;
  signOut: () => Promise<void>;
}

const SessionContext = createContext<Session | null>(null);

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession must be used inside <SessionProvider>");
  return session;
}

/** Loads the signed-in user and sends anyone without a session to /login. */
export function SessionProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const me = useQuery("me", () => api<User>("/me"));

  useEffect(() => {
    if (me.error?.status === 401) {
      // Read the location here rather than via usePathname(), which would block prerendering.
      const next = window.location.pathname + window.location.search;
      router.replace(`/login?next=${encodeURIComponent(next)}`);
    }
  }, [me.error, router]);

  const signOut = useCallback(async () => {
    await api<void>("/auth/logout", { method: "POST" });
    // Full load so no page kept alive in the background still holds this user's data.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- intentional
    window.location.assign("/login");
  }, []);

  const user = me.data ?? null;
  const canReview = user?.role === "reviewer" || user?.role === "admin";
  return (
    <SessionContext.Provider value={{ user, canReview, signOut }}>{children}</SessionContext.Provider>
  );
}
