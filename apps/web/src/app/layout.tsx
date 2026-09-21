import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Job Apply Agent",
  description: "Personal job application agent",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="header">
          <h1>Job Apply Agent</h1>
          <nav>
            <a href="/">Profile</a>
            <a href="/jobs">Jobs</a>
            <a href="/scraper">Scraper</a>
          </nav>
        </header>
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
