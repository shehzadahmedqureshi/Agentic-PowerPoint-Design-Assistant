import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Beautify Slides",
  description: "Find better slide designs without sharing raw slide text.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
