import type { Metadata } from "next";
import { TopNavbar } from "@/components/TopNavbar";
import "./globals.css";

const SITE_URL = "https://anabook-bd.vercel.app/";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
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
    images: [
      {
        url: `${process.env.NEXT_PUBLIC_BASE_PATH || ""}/logo.png`,
        width: 1024,
        height: 1024,
        alt: "AnaBook Logo",
      },
    ],
  },
  robots: {
    index: true,
    follow: true,
  },
  verification: {
    google: "an8rV3cmmY3A4FEYYgX4TbErkZP5C_EiZTJ_-p4waC4",
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
