import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dissertation Review Beta",
  description: "Private beta for APA 7 dissertation review.",
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
