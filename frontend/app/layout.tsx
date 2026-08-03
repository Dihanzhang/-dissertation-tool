import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dissertation APA 7 Review Assistant",
  description: "A careful APA 7, citation, and clarity review before dissertation submission.",
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
