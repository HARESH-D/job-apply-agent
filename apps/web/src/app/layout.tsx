import type { Metadata } from "next";
import Link from "next/link";
import { DM_Sans, Syne } from "next/font/google";
import { SideNav } from "@/components/SideNav";
import "./globals.css";

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-syne",
  display: "swap",
  weight: ["500", "600", "700"],
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Job Apply Agent",
  description: "Personal job application agent — scrape, match, tailor",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${syne.variable} ${dmSans.variable}`}>
      <body>
        <div className="app-shell">
          <aside className="sidebar">
            <Link href="/" className="wordmark">
              Job Apply
              <span>Agent</span>
            </Link>
            <SideNav />
            <p className="sidebar-foot">
              Local only. LinkedIn session stays on your machine.
            </p>
          </aside>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
