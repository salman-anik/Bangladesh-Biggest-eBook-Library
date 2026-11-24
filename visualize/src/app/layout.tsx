import type { Metadata } from "next";
import { TopNavbar } from "@/components/TopNavbar";
import "./globals.css";

const SITE_URL = "https://anabook-bd.vercel.app/";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";
const OG_IMAGE_URL = `${BASE_PATH}/logo.png`;

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default:
      "AnaBook — Bangladesh's Biggest eLibrary, PDF Library & eBook Library (29,178+ Books)",
    template: "%s | AnaBook — Bangladesh's Biggest eLibrary",
  },
  description:
    "Explore AnaBook, Bangladesh's biggest eLibrary, PDF library, and eBook library. Read and download 29,178+ free Bangla & English PDF/EPUB books, Class 1–12 NCTB textbooks, Islamic & religion books, 131+ author portraits, and the offline Android eBook reader.",
  keywords: [
    "Bangladesh Biggest eLibrary",
    "Bangladesh Biggest PDF Library",
    "Bangladesh Biggest eBook Library",
    "Bangla PDF Books",
    "Free Bangla eBooks",
    "Online PDF Library Bangladesh",
    "NCTB Class 1-12 Textbooks PDF",
    "AnaBook",
    "বাংলাদেশের বৃহত্তম ই-লাইব্রেরি",
    "বাংলা বই পিডিএফ লাইব্রেরি",
    "বাংলা ই-বুক লাইব্রেরি",
  ],
  alternates: {
    canonical: SITE_URL,
  },
  openGraph: {
    title:
      "AnaBook — Bangladesh's Biggest eLibrary, PDF Library & eBook Library",
    description:
      "29,178+ categorized Bangla & English PDF/EPUB books, Class 1–12 NCTB textbooks, Islamic & religion books, 5 reading themes, 131+ author portraits, and offline batch downloads.",
    url: SITE_URL,
    siteName: "AnaBook",
    type: "website",
    locale: "bn_BD",
    alternateLocale: ["en_US"],
    images: [
      {
        url: OG_IMAGE_URL,
        width: 1024,
        height: 1024,
        alt: "AnaBook — Bangladesh's Biggest eLibrary & PDF Book Library",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title:
      "AnaBook — Bangladesh's Biggest eLibrary, PDF Library & eBook Library",
    description:
      "Read and download 29,178+ Bangla & English PDF/EPUB books, Class 1–12 NCTB textbooks, and curated collections across Bangladesh's largest free online eLibrary.",
    images: [OG_IMAGE_URL],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  verification: {
    google: "an8rV3cmmY3A4FEYYgX4TbErkZP5C_EiZTJ_-p4waC4",
  },
};

const structuredData = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": "https://anabook-bd.vercel.app/#website",
      url: "https://anabook-bd.vercel.app/",
      name: "AnaBook — Bangladesh's Biggest eLibrary & PDF Library",
      description:
        "Bangladesh's biggest free online eLibrary, PDF library, and eBook library featuring 29,178+ Bangla & English books, NCTB Class 1–12 textbooks, and scholarly series.",
      inLanguage: ["bn", "en"],
      potentialAction: {
        "@type": "SearchAction",
        target: "https://anabook-bd.vercel.app/library/?q={search_term_string}",
        "query-input": "required name=search_term_string",
      },
    },
    {
      "@type": "Library",
      "@id": "https://anabook-bd.vercel.app/#library",
      name: "AnaBook — Bangladesh's Biggest eLibrary & PDF Library",
      url: "https://anabook-bd.vercel.app/library/",
      description:
        "Free digital archive of 29,178+ categorized Bangla & English PDF, EPUB, MOBI, and DOCX books across 8 curated categories including Education & Textbooks (Pre-Primary to Class 12), Religion Books, Authors & Scholars, and Series & Collections.",
      areaServed: {
        "@type": "Country",
        name: "Bangladesh",
      },
      inLanguage: ["bn", "en"],
    },
    {
      "@type": "FAQPage",
      "@id": "https://anabook-bd.vercel.app/#faq",
      mainEntity: [
        {
          "@type": "Question",
          name: "How can I read or download Bangla PDF and EPUB books on AnaBook?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Open the AnaBook Online Library at /library/, search by title, author, or category, and click Read to preview directly in your browser or Download to save the PDF/EPUB file.",
          },
        },
        {
          "@type": "Question",
          name: "Does AnaBook include NCTB Class 1–12 textbooks?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Yes. Under Education & Textbooks, you can filter Pre-Primary through Class 10 and Class 12 NCTB Bangla and English version textbooks in one click.",
          },
        },
        {
          "@type": "Question",
          name: "Can I bookmark books and read them offline on Android?",
          acceptedAnswer: {
            "@type": "Answer",
            text: "Yes. You can bookmark books in the Online Library Saved tab or download the free AnaBook Android app for batch offline downloads, 5 reading themes, and mistouch lock.",
          },
        },
      ],
    },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="bn">
      <body className="min-h-screen antialiased bg-white text-[#0F1115]">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
        />
        <TopNavbar />
        {children}
      </body>
    </html>
  );
}
