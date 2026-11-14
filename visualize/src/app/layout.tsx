import type { Metadata } from "next";
import "./globals.css";

const SITE_URL = "https://salman-anik.github.io/Bangladesh-Biggest-eBook-Library/";

export const metadata: Metadata = {
  title: "Bangladesh's Biggest E-Book Library | বাংলাদেশের বৃহত্তম ই-বুক লাইব্রেরি",
  description:
    "Bangladesh's Biggest E-Book Library (বাংলাদেশের বৃহত্তম ই-বুক লাইব্রেরি): Browse, search, preview, and download thousands of Bangla & English PDF/EPUB e-books, NCTB textbooks (Class 1–12), Islamic books, Bengali literature, science, engineering, and BCS preparation books on Google Drive.",
  keywords: [
    "Bangladesh Biggest Ebook Library",
    "Bangla PDF Books",
    "বাংলা বই পিডিএফ",
    "NCTB Textbooks PDF",
    "ইসলামিক বই পিডিএফ",
    "Humayun Ahmed Books PDF",
    "Rabindranath Tagore Books",
    "BCS Preparation Books PDF",
    "Bengali Literature Ebooks",
    "Free Bangla Ebooks Google Drive",
  ],
  alternates: {
    canonical: SITE_URL,
  },
  openGraph: {
    title: "Bangladesh's Biggest E-Book Library | বাংলাদেশের বৃহত্তম ই-বুক লাইব্রেরি",
    description:
      "Searchable bilingual library of Bangla & English e-books, NCTB Class 1–12 textbooks, Quran, Hadith, Bengali literature, Science & Technology across 25 categories with Google Drive links.",
    url: SITE_URL,
    siteName: "Bangladesh's Biggest E-Book Library",
    type: "website",
    locale: "bn_BD",
  },
  twitter: {
    card: "summary_large_image",
    title: "Bangladesh's Biggest E-Book Library (বাংলাদেশের বৃহত্তম ই-বুক লাইব্রেরি)",
    description:
      "Search & download thousands of Bangla PDF books, NCTB textbooks, Islamic books, Literature, Science & BCS resources directly from Google Drive.",
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
      <body className="min-h-screen antialiased bg-[#090d16] text-slate-100">
        {children}
      </body>
    </html>
  );
}
