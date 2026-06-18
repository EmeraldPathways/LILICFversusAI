import "./globals.css";
import type { Metadata } from "next";
import { AppFrame } from "@/components/AppFrame";

export const metadata: Metadata = {
  title: "Agentic AI Recommendation Demo",
  description: "Academic dashboard comparing collaborative filtering and agentic AI recommendations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppFrame>{children}</AppFrame>
      </body>
    </html>
  );
}
