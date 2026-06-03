import "./globals.css";
import type { Metadata } from "next";
import { TopNav } from "@/components/TopNav";

export const metadata: Metadata = {
  title: "H&M Recommendation Experiment",
  description: "Real-data H&M recommendation experiment comparing collaborative filtering and a 3-agent workflow.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <div className="container">
            <header className="masthead">
              <div>
                <span className="eyebrow">Offline Recommendation Experiment</span>
                <h1 className="masthead-title">H&amp;M Next-Item Recommendation Study</h1>
                <p className="masthead-copy">
                  Real H&amp;M transaction data, leave-one-out evaluation, collaborative filtering,
                  and an OpenAI-backed 3-agent ranking workflow on one dashboard.
                </p>
              </div>
              <TopNav />
            </header>
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
