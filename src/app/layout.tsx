import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nail Art World Cup",
  description: "美甲世界杯双端平台入口"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
