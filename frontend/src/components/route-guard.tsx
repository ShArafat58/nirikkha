"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { Loader } from "./loader";
import { useSession } from "./session";

// Pages anyone can open. Everything else needs an account or the demo.
const PUBLIC = ["/", "/login", "/signup", "/forgot", "/pricing", "/docs", "/admin"];

function isPublic(path: string): boolean {
  return PUBLIC.some((p) => (p === "/" ? path === "/" : path === p || path.startsWith(`${p}/`)));
}

export function RouteGuard({ children }: { children: ReactNode }) {
  const pathname = usePathname() || "/";
  const router = useRouter();
  const { signedIn, loading } = useSession();
  const open = isPublic(pathname);

  useEffect(() => {
    if (!open && !loading && !signedIn) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [open, loading, signedIn, pathname, router]);

  if (open) return <>{children}</>;
  if (loading || !signedIn) return <Loader />;
  return <>{children}</>;
}