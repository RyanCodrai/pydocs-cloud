import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "sourced.dev",
  description: "Give your coding agent access to dependency source code.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
