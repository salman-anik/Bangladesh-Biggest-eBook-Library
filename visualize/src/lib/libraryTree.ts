import type { BookItem } from "@/types/library";

export interface TreeNode {
  name: string;
  cat: string;
  sub: string;
  children: Map<string, TreeNode>;
  directBooks: BookItem[];
  totalCount: number;
  previews: BookItem[];
}

export type AuthorGroup =
  | "Bangladeshi Authors"
  | "International Authors"
  | "Islamic Scholars";

export interface AuthorItem {
  key: string;
  name: string;
  group: AuthorGroup;
  path: string[];
  count: number;
  savedCount: number;
  subfolderCount: number;
}

export interface ShortcutItem {
  label: string;
  subtitle: string;
  path: string[];
}

export const NCTB_CLASS_SHORTCUTS: ShortcutItem[] = [
  {
    label: "Pre-Primary",
    subtitle: "প্রাক-প্রাথমিক",
    path: [
      "Education & Textbooks",
      "General Education",
      "Primary Education",
      "Pre-Primary",
    ],
  },
  {
    label: "Class 1",
    subtitle: "প্রথম শ্রেণি",
    path: [
      "Education & Textbooks",
      "General Education",
      "Primary Education",
      "Class 1",
    ],
  },
  {
    label: "Class 2",
    subtitle: "দ্বিতীয় শ্রেণি",
    path: [
      "Education & Textbooks",
      "General Education",
      "Primary Education",
      "Class 2",
    ],
  },
  {
    label: "Class 3",
    subtitle: "তৃতীয় শ্রেণি",
    path: [
      "Education & Textbooks",
      "General Education",
      "Primary Education",
      "Class 3",
    ],
  },
  {
    label: "Class 4",
    subtitle: "চতুর্থ শ্রেণি",
    path: [
      "Education & Textbooks",
      "General Education",
      "Primary Education",
      "Class 4",
    ],
  },
  {
    label: "Class 5",
    subtitle: "পঞ্চম শ্রেণি",
    path: [
      "Education & Textbooks",
      "General Education",
      "Primary Education",
      "Class 5",
    ],
  },
  {
    label: "Class 6",
    subtitle: "ষষ্ঠ শ্রেণি",
    path: [
      "Education & Textbooks",
      "General Education",
      "Secondary Education",
      "Class 6",
    ],
  },
  {
    label: "Class 7",
    subtitle: "সপ্তম শ্রেণি",
    path: [
      "Education & Textbooks",
      "General Education",
      "Secondary Education",
      "Class 7",
    ],
  },
  {
    label: "Class 8",
    subtitle: "অষ্টম শ্রেণি",
    path: [
      "Education & Textbooks",
      "General Education",
      "Secondary Education",
      "Class 8",
    ],
  },
  {
    label: "Class 9",
    subtitle: "নবম শ্রেণি",
    path: [
      "Education & Textbooks",
      "General Education",
      "Secondary Education",
      "Class 9",
    ],
  },
  {
    label: "Class 10",
    subtitle: "দশম / SSC",
    path: [
      "Education & Textbooks",
      "General Education",
      "Secondary Education",
      "Class 10",
    ],
  },
  {
    label: "Class 12",
    subtitle: "দ্বাদশ / HSC",
    path: [
      "Education & Textbooks",
      "General Education",
      "Higher Secondary Education",
      "Class 12",
    ],
  },
];

export const FEATURED_AUTHOR_SHORTCUTS: ShortcutItem[] = [
  {
    label: "হুমায়ূন আহমেদ",
    subtitle: "Bangladeshi Authors",
    path: ["Authors & Scholars", "Bangladeshi Authors", "হুমায়ূন আহমেদ"],
  },
  {
    label: "রবীন্দ্রনাথ ঠাকুর",
    subtitle: "Bangladeshi Authors",
    path: ["Authors & Scholars", "Bangladeshi Authors", "রবীন্দ্রনাথ ঠাকুর"],
  },
  {
    label: "কাজী নজরুল ইসলাম",
    subtitle: "Bangladeshi Authors",
    path: ["Authors & Scholars", "Bangladeshi Authors", "কাজী নজরুল ইসলাম"],
  },
  {
    label: "মুহম্মদ জাফর ইকবাল",
    subtitle: "Bangladeshi Authors",
    path: ["Authors & Scholars", "Bangladeshi Authors", "মুহম্মদ জাফর ইকবাল"],
  },
  {
    label: "সত্যজিৎ রায়",
    subtitle: "Bangladeshi Authors",
    path: ["Authors & Scholars", "Bangladeshi Authors", "সত্যজিৎ রায়"],
  },
  {
    label: "শরৎচন্দ্র চট্টোপাধ্যায়",
    subtitle: "Bangladeshi Authors",
    path: [
      "Authors & Scholars",
      "Bangladeshi Authors",
      "শরৎচন্দ্র চট্টোপাধ্যায়",
    ],
  },
  {
    label: "বিভূতিভূষণ বন্দ্যোপাধ্যায়",
    subtitle: "Bangladeshi Authors",
    path: [
      "Authors & Scholars",
      "Bangladeshi Authors",
      "বিভূতিভূষণ বন্দ্যোপাধ্যায়",
    ],
  },
  {
    label: "আইজাক আসিমভ",
    subtitle: "International Authors",
    path: ["Authors & Scholars", "International Authors", "আইজাক আসিমভ"],
  },
];

function computeNodeStats(node: TreeNode): {
  count: number;
  previews: BookItem[];
} {
  let count = node.directBooks.length;
  const previews: BookItem[] = node.directBooks
    .filter((b) => Boolean(b.coverId))
    .slice(0, 3);

  for (const child of node.children.values()) {
    const cs = computeNodeStats(child);
    count += cs.count;
    if (previews.length < 3) {
      for (const p of cs.previews) {
        if (previews.length >= 3) break;
        previews.push(p);
      }
    }
  }
  node.totalCount = count;
  node.previews = previews;
  return { count, previews };
}

/**
 * Builds the hierarchical folder tree mirroring AnaBook ExploreScreen's exact structure,
 * including extraPaths links and Religion Books/Other Religions promotion.
 */
export function buildLibraryTree(
  books: BookItem[],
  categories: string[]
): TreeNode {
  const root: TreeNode = {
    name: "Categories",
    cat: "",
    sub: "",
    children: new Map(),
    directBooks: [],
    totalCount: 0,
    previews: [],
  };

  for (const c of categories) {
    if (c && c !== "Library Management") {
      root.children.set(c, {
        name: c,
        cat: c,
        sub: "",
        children: new Map(),
        directBooks: [],
        totalCount: 0,
        previews: [],
      });
    }
  }

  const addBookToTree = (cat: string, sub: string, book: BookItem) => {
    const catName = cat || "Other";
    let catNode = root.children.get(catName);
    if (!catNode) {
      catNode = {
        name: catName,
        cat: catName,
        sub: "",
        children: new Map(),
        directBooks: [],
        totalCount: 0,
        previews: [],
      };
      root.children.set(catName, catNode);
    }

    let curr = catNode;
    if (sub) {
      const rawParts = sub.split("/").filter(Boolean);
      const promoteOtherReligion =
        catName === "Religion Books" &&
        rawParts[0] === "Other Religions" &&
        rawParts.length >= 2;
      const parts = promoteOtherReligion ? rawParts.slice(1) : rawParts;
      let acc = promoteOtherReligion ? "Other Religions" : "";

      for (const p of parts) {
        acc = acc ? `${acc}/${p}` : p;
        let child = curr.children.get(p);
        if (!child) {
          child = {
            name: p,
            cat: catName,
            sub: acc,
            children: new Map(),
            directBooks: [],
            totalCount: 0,
            previews: [],
          };
          curr.children.set(p, child);
        }
        curr = child;
      }
    }

    if (!curr.directBooks.some((existing) => existing.id === book.id)) {
      curr.directBooks.push(book);
    }
  };

  for (const book of books) {
    addBookToTree(book.cat, book.sub, book);
    if (book.extraPaths?.length) {
      for (const ep of book.extraPaths) {
        addBookToTree(ep.cat, ep.sub, book);
      }
    }
  }

  computeNodeStats(root);
  return root;
}

/**
 * Recursively collects unique books under a TreeNode and its descendants.
 */
export function collectNodeBooks(
  node: TreeNode,
  seen = new Set<string>()
): BookItem[] {
  const result: BookItem[] = [];
  for (const b of node.directBooks) {
    if (!seen.has(b.id)) {
      seen.add(b.id);
      result.push(b);
    }
  }
  for (const child of node.children.values()) {
    result.push(...collectNodeBooks(child, seen));
  }
  return result;
}

/**
 * Extracts all authors from `Authors & Scholars` (including extraPaths) matching AnaBook's AuthorsScreen.
 */
export function extractAuthorDirectory(
  books: BookItem[],
  savedSet: Set<string>
): AuthorItem[] {
  interface MutableAcc {
    key: string;
    name: string;
    group: AuthorGroup;
    path: string[];
    bookIds: Set<string>;
    savedIds: Set<string>;
    subfolders: Set<string>;
  }

  const map = new Map<string, MutableAcc>();

  const registerPath = (book: BookItem, sub: string) => {
    const parts = sub.split("/").filter(Boolean);
    if (parts.length < 2) return;

    const topGroup = parts[0];
    let group: AuthorGroup;
    let authorName: string;
    let authorPath: string[];
    let subfolderName = "";

    if (
      topGroup === "Bangladeshi Authors" ||
      topGroup === "International Authors"
    ) {
      group = topGroup;
      authorName = parts[1];
      authorPath = ["Authors & Scholars", parts[0], parts[1]];
      if (parts.length >= 3) subfolderName = parts[2];
    } else if (topGroup === "Islamic Scholars") {
      group = "Islamic Scholars";
      if (parts.length >= 3) {
        authorName = parts[2];
        authorPath = ["Authors & Scholars", parts[0], parts[1], parts[2]];
        if (parts.length >= 4) subfolderName = parts[3];
      } else {
        authorName = parts[1];
        authorPath = ["Authors & Scholars", parts[0], parts[1]];
      }
    } else {
      return;
    }

    const key = authorPath.join("/");
    let acc = map.get(key);
    if (!acc) {
      acc = {
        key,
        name: authorName,
        group,
        path: authorPath,
        bookIds: new Set(),
        savedIds: new Set(),
        subfolders: new Set(),
      };
      map.set(key, acc);
    }
    acc.bookIds.add(book.id);
    if (savedSet.has(book.id)) acc.savedIds.add(book.id);
    if (subfolderName) acc.subfolders.add(subfolderName);
  };

  for (const book of books) {
    if (book.cat === "Authors & Scholars" && book.sub) {
      registerPath(book, book.sub);
    }
    if (book.extraPaths) {
      for (const ep of book.extraPaths) {
        if (ep.cat === "Authors & Scholars" && ep.sub) {
          registerPath(book, ep.sub);
        }
      }
    }
  }

  const list: AuthorItem[] = [];
  for (const acc of map.values()) {
    list.push({
      key: acc.key,
      name: acc.name,
      group: acc.group,
      path: acc.path,
      count: acc.bookIds.size,
      savedCount: acc.savedIds.size,
      subfolderCount: acc.subfolders.size,
    });
  }

  list.sort((a, b) =>
    a.name.localeCompare(b.name, undefined, {
      numeric: true,
      sensitivity: "base",
    })
  );
  return list;
}
