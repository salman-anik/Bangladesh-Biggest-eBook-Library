import type { Metadata } from "next";
import { LibraryExplorer } from "@/components/LibraryExplorer";

const LIBRARY_URL = "https://anabook-bd.vercel.app/library/";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";
const OG_IMAGE_URL = `${BASE_PATH}/logo.png`;

export const metadata: Metadata = {
  title:
    "Online Library — Bangladesh's Biggest PDF Library & eBook Library (29,178+ Books)",
  description:
    "Search, read online, and download 29,178+ Bangla & English PDF, EPUB, and MOBI books, NCTB Class 1–12 textbooks, Religion Books, and Series Collections in Bangladesh's biggest free eLibrary.",
  alternates: {
    canonical: LIBRARY_URL,
  },
  openGraph: {
    title:
      "AnaBook Online Library — Bangladesh's Biggest PDF & eBook Library (29,178+ Books)",
    description:
      "Browse 29,178+ free Bangla & English PDF/EPUB books, Pre-Primary to Class 12 NCTB textbooks, Authors & Scholars, and Series Collections in Bangladesh's biggest digital eLibrary.",
    url: LIBRARY_URL,
    siteName: "AnaBook",
    type: "website",
    locale: "bn_BD",
    alternateLocale: ["en_US"],
    images: [
      {
        url: OG_IMAGE_URL,
        width: 1024,
        height: 1024,
        alt: "AnaBook Online Library — Bangladesh's Biggest eLibrary",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title:
      "AnaBook Online Library — Bangladesh's Biggest PDF & eBook Library",
    description:
      "Search and download 29,178+ Bangla & English PDF/EPUB books and Class 1–12 NCTB textbooks free.",
    images: [OG_IMAGE_URL],
  },
};

const librarySchema = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "BreadcrumbList",
      itemListElement: [
        {
          "@type": "ListItem",
          position: 1,
          name: "Home",
          item: "https://anabook-bd.vercel.app/",
        },
        {
          "@type": "ListItem",
          position: 2,
          name: "Online Library",
          item: LIBRARY_URL,
        },
      ],
    },
    {
      "@type": "CollectionPage",
      "@id": `${LIBRARY_URL}#collection`,
      url: LIBRARY_URL,
      name: "AnaBook Online Library — Bangladesh's Biggest PDF & eBook Library",
      description:
        "Browse and search 29,178+ Bangla & English books, NCTB Class 1–12 textbooks, Islamic & religion books, authors, and series collections.",
      inLanguage: ["bn", "en"],
      isPartOf: {
        "@id": "https://anabook-bd.vercel.app/#website",
      },
    },
  ],
};

export default function OnlineLibraryPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(librarySchema) }}
      />
      <LibraryExplorer />
    </>
  );
}
