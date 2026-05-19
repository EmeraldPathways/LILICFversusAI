import "./globals.css";
import type { Metadata } from "next";
import { TopNav } from "@/components/TopNav";

export const metadata: Metadata = {
  title: "Agentic AI Recommendation Demo",
  description: "Academic dashboard comparing collaborative filtering and agentic AI recommendations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <div className="container">
            <header className="hero">
              <span className="eyebrow">Offline E-commerce Experiment</span>
              <h1>Agentic AI Recommendation Framework</h1>
              <p>
                A research demo comparing collaborative filtering against an explainable,
                feedback-aware recommendation decision layer built on the H&amp;M dataset.
              </p>
              <TopNav />
            </header>
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
