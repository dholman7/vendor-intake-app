import { AppHeader } from "@/components/app-header";
import { SessionProvider } from "@/lib/session";

export default function AppLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <SessionProvider>
      <AppHeader />
      {children}
    </SessionProvider>
  );
}
