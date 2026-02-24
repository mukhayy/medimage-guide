import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MedGemma User Guide - AI MRI Analysis",
  description:
    "Interactive MRI diagnosis with real-time region highlighting using MedGemma and MedSAM2",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">{children}</body>
    </html>
  );
}
