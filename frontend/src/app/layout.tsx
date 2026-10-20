import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Noto_Sans_Bengali } from "next/font/google";

import { Providers } from "../components/providers";
import { SessionProvider } from "../components/session";
import { SiteHeader } from "../components/site-header";
import "./globals.css";

const sans = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-plex-sans", display: "swap" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-plex-mono", display: "swap" });
const bengali = Noto_Sans_Bengali({ subsets: ["bengali"], weight: ["400", "500", "700"], variable: "--font-noto-bn", display: "swap" });

export const metadata: Metadata = {
  title: "Nirikkha - Governance Crash-Test AI",
  description: "Trust less, Verify more. Test the governance evidence behind a critical decision before you make it.",
};

// Applies the saved theme and language before the first paint (no flash).
const BOOT = `try{var d=document.documentElement;if(localStorage.getItem("nirikkha.theme")==="paper")d.dataset.theme="paper";if(localStorage.getItem("nirikkha.lang")==="bn")d.lang="bn"}catch(e){}`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning
          className={`${sans.variable} ${mono.variable} ${bengali.variable}`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: BOOT }} />
      </head>
      <body className="min-h-screen bg-bg text-text antialiased">
        <Providers>
          <SessionProvider>
            <SiteHeader />
            {children}
          </SessionProvider>
        </Providers>
      </body>
    </html>
  );
}