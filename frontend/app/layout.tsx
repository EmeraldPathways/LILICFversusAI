import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Agentic AI Recommendation Demo",
  description: "Academic dashboard comparing collaborative filtering and agentic AI recommendations.",
};

const links = [
  ["/", "Overview"],
  ["/research-setup", "Research Setup"],
  ["/data-processing", "Data Processing"],
  ["/user-intention", "User Intention"],
  ["/comparison", "Comparison"],
  ["/evaluation", "Evaluation"],
] as const;

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
              <nav className="nav">
                {links.map(([href, label]) => (
                  <Link key={href} href={href}>
                    {label}
                  </Link>
                ))}
              </nav>
            </header>
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
