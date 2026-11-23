import type { Metadata } from "next";
import { TopNavbar } from "@/components/TopNavbar";
import "./globals.css";

const SITE_URL = "https://anabook.vercel.app/";

export const metadata: Metadata = {
  title: "AnaBook — Read 22,166+ Bangla & Academic Books Offline",
  description:
    "AnaBook is a free offline-first Android eBook reader and Online Library with 22,166+ Bangla & English books, Class 1–12 NCTB textbooks, 131+ author portraits, and full-screen mistouch lock.",
  keywords: [
    "AnaBook",
    "Bangladesh Biggest Ebook Library",
    "Bangla PDF Books App",
    "NCTB Class 1-12 App",
    "বাংলা বই পিডিএফ অ্যাপ",
    "Offline eBook Reader Android",
  ],
  alternates: {
    canonical: SITE_URL,
  },
  openGraph: {
    title: "AnaBook — Offline Android eBook App & Online Library",
    description:
      "22,166+ categorized books, Class 1–12 NCTB textbooks, 5 reading themes, 131+ author portraits, batch offline downloads & full-screen mistouch lock.",
    url: SITE_URL,
    siteName: "AnaBook",
    type: "website",
    locale: "bn_BD",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="bn">
      <body className="min-h-screen antialiased bg-white text-[#0F1115]">
        <TopNavbar />
        {children}
      </body>
    </html>
  );
}
