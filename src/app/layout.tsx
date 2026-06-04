import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "美甲热点 Review",
  description: "基于小红书实时趋势生成今日运营日报与款式调整建议"
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
