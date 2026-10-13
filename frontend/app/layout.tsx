import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DriveLens AI — Read-Only Document Intelligence Assistant",
  description: "Connect your Google Drive in strictly read-only mode to extract key facts and summaries from your most recent document.",
  keywords: ["Google Drive", "AI Assistant", "Document Intelligence", "OpenAI", "Read-Only OAuth"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>{children}</body>
    </html>
  );
}
