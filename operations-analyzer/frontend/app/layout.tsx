import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Operations Analyzer — Rappi",
  description: "Bot de datos e insights automáticos para Operations",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="bg-white text-gray-900 min-h-screen">{children}</body>
    </html>
  );
}
