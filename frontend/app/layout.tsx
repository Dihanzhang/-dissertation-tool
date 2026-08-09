import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "APA 7 Review Tool",
  description: "Rule-based APA 7 checks for essays, research papers and dissertations.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
