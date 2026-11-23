import type { Metadata } from "next";
import "./globals.css";

const SITE_URL = "https://salman-anik.github.io/Bangladesh-Biggest-eBook-Library/";

export const metadata: Metadata = {
  title: "Bangladesh eBook Library | Offline-First Android App & Online Archive",
  description:
    "Read 22,166+ Bangla, English & Arabic eBooks, NCTB Class 1–12 textbooks, university courses, and classics offline with the Bangladesh eBook Library Android App, or browse the complete Online Library.",
  keywords: [
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
    title: "Bangladesh eBook Library — Offline Android App & Online Library",
    description:
      "22,166+ categorized books, Class 1–12 NCTB textbooks, 5 Pinterest-inspired reading themes, 131+ author portraits, batch section offline downloads & full-screen mistouch lock.",
    url: SITE_URL,
    siteName: "Bangladesh eBook Library",
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
    <html lang="bn" className="dark">
      <body className="min-h-screen antialiased bg-[#11100F] text-[#F7F3EE]">
        {children}
      </body>
    </html>
  );
}
