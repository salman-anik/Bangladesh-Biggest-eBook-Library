import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import { AuthorAvatar } from '../components/AuthorAvatar';
import { AuthorDetailModal } from '../components/AuthorDetailModal';
import { BookCover } from '../components/BookCover';
import { CategoryIcon } from '../components/CategoryIcon';
import {
  ArrowLeftIcon,
  BookOpenIcon,
  ChevronRightIcon,
  CloseIcon,
  DownloadIcon,
  OfflineIcon,
  SearchIcon,
} from '../components/Icons';
import { useAppTheme } from '../context/ThemeContext';
import type { BatchDownloadStatus, Book, OfflineBookEntry, ThemeMode } from '../types';
import { useHorizontalScrollLock } from '../utils/horizontalScrollLock';

const SECTION_PAGE_SIZE = 24;

interface AuthorDetailRecord {
  name?: string;
  group?: string;
  shortDesc?: string;
  bio?: string;
  wikiUrl?: string;
}

// eslint-disable-next-line @typescript-eslint/no-var-requires
const AUTHOR_DETAILS: Record<string, AuthorDetailRecord> = require('../../assets/author_details.json');

function lookupAuthorDetail(name: string): AuthorDetailRecord | undefined {
  const raw = (name || '').trim().toLowerCase();
  if (!raw) return undefined;
  if (AUTHOR_DETAILS[raw]) return AUTHOR_DETAILS[raw];
  return AUTHOR_DETAILS[raw.normalize('NFC')];
}

interface Props {
  books: Book[];
  categories: string[];
  offlineById: Record<string, OfflineBookEntry>;
  downloadingMap: Record<string, number>;
  path: string[];
  onChangePath: (nextPath: string[]) => void;
  batchDownload: BatchDownloadStatus | null;
  onOpenDetail: (book: Book) => void;
  onQuickRead: (book: Book) => void;
  onMakeOffline: (book: Book) => void;
  onDownloadFolderOffline: (folderName: string, folderBooks: Book[]) => void;
  onCancelBatchDownload: () => void;
  onBrowseFiltered: (cat: string, sub: string) => void;
  onHorizontalTouchLock?: (locked: boolean) => void;
}

interface TreeNode {
  name: string;
  cat: string;
  sub: string;
  children: Map<string, TreeNode>;
  directBooks: Book[];
  totalCount: number;
  previews: Book[];
}

function computeNodeStats(node: TreeNode): { count: number; previews: Book[] } {
  let count = node.directBooks.length;
  const previews: Book[] = node.directBooks.filter((b) => Boolean(b.coverId)).slice(0, 3);

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

function collectNodeBooks(node: TreeNode): Book[] {
  const result: Book[] = [...node.directBooks];
  for (const child of node.children.values()) {
    result.push(...collectNodeBooks(child));
  }
  return result;
}

function countOfflineInNode(node: TreeNode, offlineById: Record<string, OfflineBookEntry>): number {
  let c = 0;
  for (const b of node.directBooks) {
    if (offlineById[b.id]) c++;
  }
  for (const child of node.children.values()) {
    c += countOfflineInNode(child, offlineById);
  }
  return c;
}

interface CategoryPalette {
  bg: string;
  border: string;
  orb: string;
  badgeBg: string;
  accent: string;
}

const BENTO_PALETTES: Record<string, { dark: CategoryPalette; light: CategoryPalette }> = {
  bangla: {
    dark: { bg: '#2B1815', border: '#4A2823', orb: 'rgba(229, 128, 102, 0.16)', badgeBg: 'rgba(0, 0, 0, 0.34)', accent: '#F2A38F' },
    light: { bg: '#FCEEE9', border: '#F0CFC3', orb: 'rgba(210, 100, 72, 0.14)', badgeBg: 'rgba(255, 255, 255, 0.80)', accent: '#9E4029' },
  },
  religion: {
    dark: { bg: '#132620', border: '#23453A', orb: 'rgba(95, 194, 154, 0.16)', badgeBg: 'rgba(0, 0, 0, 0.34)', accent: '#8BE0BC' },
    light: { bg: '#E8F5EF', border: '#C2E3D4', orb: 'rgba(46, 138, 102, 0.14)', badgeBg: 'rgba(255, 255, 255, 0.80)', accent: '#1F6B4E' },
  },
  education: {
    dark: { bg: '#161F33', border: '#283A5E', orb: 'rgba(116, 160, 245, 0.16)', badgeBg: 'rgba(0, 0, 0, 0.34)', accent: '#9CC0FF' },
    light: { bg: '#EBF1FC', border: '#C7D8F7', orb: 'rgba(62, 108, 204, 0.14)', badgeBg: 'rgba(255, 255, 255, 0.80)', accent: '#274E9E' },
  },
  authors: {
    dark: { bg: '#292012', border: '#4A381D', orb: 'rgba(235, 182, 88, 0.16)', badgeBg: 'rgba(0, 0, 0, 0.34)', accent: '#F4C97A' },
    light: { bg: '#FDF4E3', border: '#F2DAB0', orb: 'rgba(196, 136, 36, 0.14)', badgeBg: 'rgba(255, 255, 255, 0.80)', accent: '#8F5B0A' },
  },
  series: {
    dark: { bg: '#25172E', border: '#442A54', orb: 'rgba(198, 132, 242, 0.16)', badgeBg: 'rgba(0, 0, 0, 0.34)', accent: '#D8A6FC' },
    light: { bg: '#F4ECFA', border: '#DEC7F0', orb: 'rgba(136, 68, 194, 0.14)', badgeBg: 'rgba(255, 255, 255, 0.80)', accent: '#6B2A9E' },
  },
  reference: {
    dark: { bg: '#122429', border: '#21424B', orb: 'rgba(86, 198, 214, 0.16)', badgeBg: 'rgba(0, 0, 0, 0.34)', accent: '#8AE0EC' },
    light: { bg: '#E7F6F8', border: '#BFE4EA', orb: 'rgba(34, 140, 158, 0.14)', badgeBg: 'rgba(255, 255, 255, 0.80)', accent: '#126473' },
  },
  english: {
    dark: { bg: '#2C1622', border: '#4D263C', orb: 'rgba(238, 120, 174, 0.16)', badgeBg: 'rgba(0, 0, 0, 0.34)', accent: '#F69EC5' },
    light: { bg: '#FCECF3', border: '#F2C7DA', orb: 'rgba(194, 58, 118, 0.14)', badgeBg: 'rgba(255, 255, 255, 0.80)', accent: '#992257' },
  },
  slate: {
    dark: { bg: '#1F2024', border: '#35373F', orb: 'rgba(164, 170, 186, 0.15)', badgeBg: 'rgba(0, 0, 0, 0.34)', accent: '#C2C7D4' },
    light: { bg: '#F1F2F5', border: '#D7DBE2', orb: 'rgba(104, 112, 128, 0.13)', badgeBg: 'rgba(255, 255, 255, 0.80)', accent: '#454C59' },
  },
};

const BENTO_FALLBACK_KEYS = ['bangla', 'religion', 'education', 'authors', 'series', 'reference', 'english', 'slate'] as const;

function getCategoryPalette(name: string, mode: ThemeMode): CategoryPalette {
  const low = (name || '').toLowerCase();
  let key: (typeof BENTO_FALLBACK_KEYS)[number] | undefined;
  if (low.includes('bangla books')) key = 'bangla';
  else if (low.includes('religion')) key = 'religion';
  else if (low.includes('education')) key = 'education';
  else if (low.includes('authors')) key = 'authors';
  else if (low.includes('series')) key = 'series';
  else if (low.includes('reference')) key = 'reference';
  else if (low.includes('english')) key = 'english';
  else if (low.includes('review') || low.includes('unclassified')) key = 'slate';

  if (!key) {
    let hash = 0;
    for (let i = 0; i < low.length; i++) {
      hash = ((hash * 31) + low.charCodeAt(i)) >>> 0;
    }
    key = BENTO_FALLBACK_KEYS[hash % BENTO_FALLBACK_KEYS.length];
  }
  return BENTO_PALETTES[key][mode];
}

export const ExploreScreen = React.memo(function ExploreScreen({
  books,
  categories,
  offlineById,
  downloadingMap,
  path,
  onChangePath,
  batchDownload,
  onOpenDetail,
  onQuickRead,
  onMakeOffline,
  onDownloadFolderOffline,
  onCancelBatchDownload,
  onBrowseFiltered,
  onHorizontalTouchLock,
}: Props) {
  const { theme, mode, fs } = useAppTheme();
  const hLockProps = useHorizontalScrollLock(onHorizontalTouchLock);
  const [filterText, setFilterText] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [visibleSectionCount, setVisibleSectionCount] = useState(SECTION_PAGE_SIZE);
  const [authorModalOpen, setAuthorModalOpen] = useState(false);

  const pathKey = path.join('/');
  useEffect(() => {
    setVisibleSectionCount(SECTION_PAGE_SIZE);
  }, [pathKey, filterText]);

  useEffect(() => {
    setAuthorModalOpen(false);
  }, [pathKey]);

  const updatePath = (next: string[]) => {
    setFilterText('');
    onChangePath(next);
  };

  const rootTree = useMemo(() => {
    const root: TreeNode = {
      name: 'Categories',
      cat: '',
      sub: '',
      children: new Map(),
      directBooks: [],
      totalCount: 0,
      previews: [],
    };

    for (const c of categories) {
      if (c && c !== 'Library Management') {
        root.children.set(c, {
          name: c,
          cat: c,
          sub: '',
          children: new Map(),
          directBooks: [],
          totalCount: 0,
          previews: [],
        });
      }
    }

    for (const book of books) {
      let catNode = root.children.get(book.cat);
      if (!catNode) {
        catNode = {
          name: book.cat,
          cat: book.cat,
          sub: '',
          children: new Map(),
          directBooks: [],
          totalCount: 0,
          previews: [],
        };
        root.children.set(book.cat, catNode);
      }
      let curr = catNode;
      if (book.sub) {
        const rawParts = book.sub.split('/').filter(Boolean);
        const promoteOtherReligion =
          book.cat === 'Religion Books' &&
          rawParts[0] === 'Other Religions' &&
          rawParts.length >= 2;
        const parts = promoteOtherReligion ? rawParts.slice(1) : rawParts;
        let acc = promoteOtherReligion ? 'Other Religions' : '';
        for (const p of parts) {
          acc = acc ? `${acc}/${p}` : p;
          let child = curr.children.get(p);
          if (!child) {
            child = {
              name: p,
              cat: book.cat,
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
      curr.directBooks.push(book);
    }

    computeNodeStats(root);
    return root;
  }, [books, categories]);

  const currentNode = useMemo(() => {
    let curr = rootTree;
    for (const seg of path) {
      const next = curr.children.get(seg);
      if (!next) break;
      curr = next;
    }
    return curr;
  }, [rootTree, path]);

  const childSections = useMemo(() => {
    const q = filterText.trim().toLowerCase();
    const list = Array.from(currentNode.children.values()).filter((n) => n.totalCount > 0);
    if (path.length > 0) {
      list.sort((a, b) =>
        a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' })
      );
    }
    return q ? list.filter((n) => n.name.toLowerCase().includes(q)) : list;
  }, [currentNode, filterText, path.length]);

  const directBooksFiltered = useMemo(() => {
    const q = filterText.trim().toLowerCase();
    const list = currentNode.directBooks;
    if (!q) return list;
    return list.filter((b) => b.searchBlob.includes(q));
  }, [currentNode, filterText]);

  const isRoot = path.length === 0;

  const allNodeBooks = useMemo(
    () => (isRoot ? [] : collectNodeBooks(currentNode)),
    [isRoot, currentNode]
  );

  const remainingCount = useMemo(() => {
    if (isRoot || !allNodeBooks.length) return 0;
    let rem = 0;
    for (const b of allNodeBooks) {
      if (!offlineById[b.id]) rem++;
    }
    return rem;
  }, [isRoot, allNodeBooks, offlineById]);

  const isAuthorsLeafGrid = useMemo(() => {
    if (path[0] !== 'Authors & Scholars' || childSections.length === 0) return false;
    return (
      ((path[1] === 'Bangladeshi Authors' || path[1] === 'International Authors') && path.length === 2) ||
      (path[1] === 'Islamic Scholars' && path.length === 3)
    );
  }, [path, childSections.length]);

  const visibleChildSections = useMemo(
    () => childSections.slice(0, visibleSectionCount),
    [childSections, visibleSectionCount]
  );

  const loadMoreSections = useCallback(() => {
    setVisibleSectionCount((n) => (n < childSections.length ? Math.min(childSections.length, n + SECTION_PAGE_SIZE) : n));
  }, [childSections.length]);

  const renderSectionCard = useCallback(
    (subNode: TreeNode) => {
      const subOffline = countOfflineInNode(subNode, offlineById);
      if (isAuthorsLeafGrid) {
        return (
          <TouchableOpacity
            key={subNode.name}
            style={[styles.authorCard, { backgroundColor: theme.surface, borderColor: theme.border }]}
            onPress={() => updatePath([...path, subNode.name])}
            activeOpacity={0.84}
          >
            <AuthorAvatar name={subNode.name} size={64} />
            <Text
              style={[styles.authorCardName, { color: theme.ink, fontSize: fs(13) }]}
              numberOfLines={2}
            >
              {subNode.name}
            </Text>
            <View style={[styles.miniPill, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
              <Text style={[styles.miniPillText, { color: theme.accent, fontSize: fs(10.5) }]}>
                {subNode.totalCount.toLocaleString()} books
                {subOffline > 0 ? ` · ${subOffline} saved` : ''}
              </Text>
            </View>
          </TouchableOpacity>
        );
      }

      const pal = getCategoryPalette(subNode.name, mode);
      const subCover = subNode.previews[0];
      return (
        <TouchableOpacity
          key={subNode.name}
          style={[styles.bentoSubCard, { backgroundColor: pal.bg, borderColor: pal.border }]}
          onPress={() => updatePath([...path, subNode.name])}
          activeOpacity={0.86}
        >
          <View style={[styles.bentoSubOrb, { backgroundColor: pal.orb }]} />

          <Text
            style={[styles.bentoSubTitle, { color: theme.ink, fontSize: fs(13) }]}
            numberOfLines={2}
          >
            {subNode.name}
          </Text>

          <View style={styles.bentoSubBottomLeft}>
            <View style={[styles.bentoCountPill, { backgroundColor: pal.badgeBg }]}>
              <Text style={[styles.bentoCountText, { color: pal.accent, fontSize: fs(10) }]} numberOfLines={1}>
                {subNode.totalCount.toLocaleString()} books
              </Text>
              {subOffline > 0 ? <OfflineIcon size={12} color={theme.sage} /> : null}
            </View>
          </View>

          {subCover ? (
            <View style={styles.bentoSubCover} pointerEvents="none">
              <BookCover
                book={subCover}
                localCoverUri={offlineById[subCover.id]?.coverLocalUri}
                width={44}
                height={64}
                borderRadius={5}
              />
            </View>
          ) : (
            <View style={styles.bentoSubWatermark} pointerEvents="none">
              <CategoryIcon name={subNode.name} size={38} />
            </View>
          )}
        </TouchableOpacity>
      );
    },
    [offlineById, isAuthorsLeafGrid, theme, fs, path, mode]
  );

  const isViewingAuthor = Boolean(
    path[0] === 'Authors & Scholars' &&
      ((path[1] !== 'Islamic Scholars' && path.length === 3) ||
        (path[1] === 'Islamic Scholars' && path.length === 4))
  );

  const authorDetail = useMemo(
    () => (isViewingAuthor ? lookupAuthorDetail(currentNode.name) : undefined),
    [isViewingAuthor, currentNode.name]
  );

  const authorProfileBanner = isViewingAuthor ? (
    <TouchableOpacity
      style={[styles.authorBannerCard, { backgroundColor: theme.surface, borderColor: theme.border }]}
      onPress={() => setAuthorModalOpen(true)}
      activeOpacity={0.86}
    >
      <View style={styles.authorBannerTop}>
        <AuthorAvatar name={currentNode.name} size={52} />
        <View style={styles.authorBannerInfo}>
          <Text style={[styles.authorBannerName, { color: theme.ink, fontSize: fs(15.5) }]} numberOfLines={1}>
            {currentNode.name}
          </Text>
          <Text style={[styles.authorBannerSub, { color: theme.accent, fontSize: fs(11.5) }]} numberOfLines={1}>
            {authorDetail?.shortDesc || path[1] || 'Author'} · {currentNode.totalCount.toLocaleString()} books
          </Text>
        </View>
        <View style={[styles.authorDetailsBtn, { backgroundColor: theme.accentSoft, borderColor: theme.accent }]}>
          <Text style={[styles.authorDetailsBtnText, { color: theme.accent, fontSize: fs(11) }]}>
            Author Details
          </Text>
        </View>
      </View>
      {authorDetail?.bio ? (
        <Text style={[styles.authorBannerBio, { color: theme.muted, fontSize: fs(12) }]} numberOfLines={2}>
          {authorDetail.bio}
        </Text>
      ) : null}
    </TouchableOpacity>
  ) : undefined;

  const batchPct =
    batchDownload && batchDownload.total > 0
      ? Math.min(100, Math.round(((batchDownload.completed + batchDownload.failed) / batchDownload.total) * 100))
      : 0;

  const isDownloadingThisSection = Boolean(
    batchDownload && !isRoot && batchDownload.folderName === currentNode.name
  );

  return (
    <View style={[styles.root, { backgroundColor: theme.bg }]}>
      {/* Single Clean Header Row (No second subtitle) */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          {!isRoot ? (
            <TouchableOpacity
              style={[styles.iconCircle, { backgroundColor: theme.surface, borderColor: theme.border }]}
              onPress={() => updatePath(path.slice(0, -1))}
              accessibilityLabel="Back"
            >
              <ArrowLeftIcon size={18} color={theme.ink} />
            </TouchableOpacity>
          ) : null}

          {isViewingAuthor ? (
            <AuthorAvatar name={currentNode.name} size={36} />
          ) : !isRoot ? (
            <CategoryIcon name={currentNode.name} size={28} />
          ) : null}

          <Text style={[styles.heading, { color: theme.ink, fontSize: fs(21) }]} numberOfLines={1}>
            {isRoot ? 'Categories' : currentNode.name}
          </Text>
        </View>

        {isRoot ? (
          <View style={[styles.headerTotalPill, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
            <Text style={[styles.headerTotalText, { color: theme.accent, fontSize: fs(11.5) }]}>
              {books.length.toLocaleString()} books
            </Text>
          </View>
        ) : (
          <View style={styles.headerActions}>
            <TouchableOpacity
              style={[styles.iconCircle, { backgroundColor: theme.surface, borderColor: theme.border }]}
              onPress={() => onBrowseFiltered(currentNode.cat, currentNode.sub)}
              accessibilityLabel="Search in Library"
            >
              <SearchIcon size={17} color={theme.ink} />
            </TouchableOpacity>

            {allNodeBooks.length > 0 ? (
              isDownloadingThisSection ? (
                <TouchableOpacity
                  style={[styles.iconCircle, { backgroundColor: theme.danger, borderColor: theme.danger }]}
                  onPress={onCancelBatchDownload}
                  accessibilityLabel="Cancel section download"
                >
                  <CloseIcon size={17} color={theme.creamInk} />
                </TouchableOpacity>
              ) : remainingCount === 0 ? (
                <View
                  style={[styles.iconCircle, { backgroundColor: theme.sage, borderColor: theme.sage }]}
                  accessibilityLabel="Full section available offline"
                >
                  <OfflineIcon size={18} color={theme.ink} />
                </View>
              ) : (
                <TouchableOpacity
                  style={[
                    styles.iconCircle,
                    { backgroundColor: theme.accent, borderColor: theme.accent },
                    Boolean(batchDownload) && { opacity: 0.5 },
                  ]}
                  disabled={Boolean(batchDownload)}
                  onPress={() => onDownloadFolderOffline(currentNode.name, allNodeBooks)}
                  accessibilityLabel="Download full section offline"
                >
                  <DownloadIcon size={18} color={theme.creamInk} />
                </TouchableOpacity>
              )
            ) : null}
          </View>
        )}
      </View>

      {/* Active Batch Download Banner */}
      {batchDownload ? (
        <View style={[styles.batchBanner, { backgroundColor: theme.surface, borderColor: theme.accent }]}>
          <View style={styles.batchTopRow}>
            <Text style={[styles.batchTitle, { color: theme.ink, fontSize: fs(12) }]} numberOfLines={1}>
              {batchDownload.folderName} · {batchDownload.completed}/{batchDownload.total}
            </Text>
            <TouchableOpacity
              style={[styles.batchCancelIcon, { backgroundColor: theme.surfaceAlt, borderColor: theme.danger }]}
              onPress={onCancelBatchDownload}
            >
              <CloseIcon size={14} color={theme.danger} />
            </TouchableOpacity>
          </View>
          <Text style={[styles.batchCurrentTitle, { color: theme.muted, fontSize: fs(11) }]} numberOfLines={1}>
            {batchDownload.currentTitle || 'Downloading…'}
          </Text>
          <View style={[styles.batchTrack, { backgroundColor: theme.surfaceAlt }]}>
            <View style={[styles.batchFill, { width: `${Math.max(4, batchPct)}%`, backgroundColor: theme.accent }]} />
          </View>
        </View>
      ) : null}

      {/* Minimal Breadcrumbs when >= 2 levels deep */}
      {path.length >= 2 ? (
        <View style={styles.crumbOuter}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.crumbScroll} {...hLockProps}>
            <TouchableOpacity
              style={[styles.crumbChip, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
              onPress={() => updatePath([])}
            >
              <Text style={[styles.crumbText, { color: theme.cream, fontSize: fs(11) }]}>All</Text>
            </TouchableOpacity>
            {path.map((seg, idx) => {
              const last = idx === path.length - 1;
              return (
                <React.Fragment key={`${seg}-${idx}`}>
                  <ChevronRightIcon size={13} color={theme.muted} />
                  <TouchableOpacity
                    style={[
                      styles.crumbChip,
                      {
                        backgroundColor: last ? theme.cream : theme.surfaceAlt,
                        borderColor: last ? theme.cream : theme.border,
                      },
                    ]}
                    onPress={() => updatePath(path.slice(0, idx + 1))}
                  >
                    <Text
                      style={[
                        styles.crumbText,
                        { color: last ? theme.creamInk : theme.cream, fontSize: fs(11) },
                        last && styles.crumbTextActive,
                      ]}
                    >
                      {seg}
                    </Text>
                  </TouchableOpacity>
                </React.Fragment>
              );
            })}
          </ScrollView>
        </View>
      ) : null}

      {/* Search Filter */}
      <View style={styles.searchWrap}>
        <View style={[styles.searchBox, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
          <SearchIcon size={16} color={theme.muted} />
          <TextInput
            style={[styles.filterInput, { color: theme.ink, fontSize: fs(13) }]}
            placeholder={isRoot ? 'Filter categories…' : 'Search here…'}
            placeholderTextColor={theme.muted}
            value={filterText}
            onChangeText={setFilterText}
          />
          {filterText.length > 0 ? (
            <TouchableOpacity onPress={() => setFilterText('')}>
              <CloseIcon size={15} color={theme.muted} />
            </TouchableOpacity>
          ) : null}
        </View>
      </View>

      {/* 2-Column Color-Tinted Bento Grid (Root) OR Subcategories + Books */}
      {isRoot ? (
        <ScrollView contentContainerStyle={styles.bentoGridWrap} showsVerticalScrollIndicator={false}>
          {childSections.map((node) => {
            const pal = getCategoryPalette(node.name, mode);
            const coverFront = node.previews[0];
            const coverBack = node.previews[1];
            return (
              <TouchableOpacity
                key={node.name}
                style={[styles.bentoRootCard, { backgroundColor: pal.bg, borderColor: pal.border }]}
                onPress={() => updatePath([node.name])}
                activeOpacity={0.86}
              >
                <View style={[styles.bentoOrb, { backgroundColor: pal.orb }]} />

                <View style={styles.bentoTopWrap}>
                  <View style={[styles.bentoIconBadge, { backgroundColor: pal.badgeBg }]}>
                    <CategoryIcon name={node.name} size={20} />
                  </View>
                  <Text
                    style={[styles.bentoTitle, { color: theme.ink, fontSize: fs(14.5) }]}
                    numberOfLines={2}
                  >
                    {node.name}
                  </Text>
                </View>

                <View style={styles.bentoBottomLeft}>
                  <View style={[styles.bentoCountPill, { backgroundColor: pal.badgeBg }]}>
                    <Text style={[styles.bentoCountText, { color: pal.accent, fontSize: fs(10.5) }]} numberOfLines={1}>
                      {node.totalCount.toLocaleString()} books
                    </Text>
                  </View>
                </View>

                {coverFront ? (
                  <View style={styles.bentoCoverCluster} pointerEvents="none">
                    {coverBack ? (
                      <View style={styles.bentoCoverBack}>
                        <BookCover
                          book={coverBack}
                          localCoverUri={offlineById[coverBack.id]?.coverLocalUri}
                          width={48}
                          height={70}
                          borderRadius={6}
                        />
                      </View>
                    ) : null}
                    <View style={styles.bentoCoverFront}>
                      <BookCover
                        book={coverFront}
                        localCoverUri={offlineById[coverFront.id]?.coverLocalUri}
                        width={56}
                        height={82}
                        borderRadius={7}
                      />
                    </View>
                  </View>
                ) : (
                  <View style={styles.bentoWatermark} pointerEvents="none">
                    <CategoryIcon name={node.name} size={52} />
                  </View>
                )}
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      ) : directBooksFiltered.length === 0 && childSections.length > 0 ? (
        <FlatList
          key={isAuthorsLeafGrid ? 'authors-grid-2' : 'sub-bento-2'}
          numColumns={2}
          columnWrapperStyle={styles.twoColRow}
          data={visibleChildSections}
          keyExtractor={(item) => item.name}
          initialNumToRender={12}
          maxToRenderPerBatch={10}
          windowSize={5}
          removeClippedSubviews
          contentContainerStyle={styles.drillContent}
          showsVerticalScrollIndicator={false}
          onEndReached={loadMoreSections}
          onEndReachedThreshold={0.7}
          ListHeaderComponent={authorProfileBanner}
          renderItem={({ item }) => renderSectionCard(item)}
        />
      ) : (
        <FlatList
          key={viewMode === 'grid' ? 'explore-grid-3' : 'explore-list-1'}
          numColumns={viewMode === 'grid' ? 3 : 1}
          columnWrapperStyle={viewMode === 'grid' ? styles.bookGridRow : undefined}
          data={directBooksFiltered}
          keyExtractor={(item) => item.id}
          initialNumToRender={12}
          maxToRenderPerBatch={12}
          windowSize={5}
          removeClippedSubviews
          contentContainerStyle={styles.drillContent}
          showsVerticalScrollIndicator={false}
          ListHeaderComponent={
            authorProfileBanner || childSections.length > 0 || directBooksFiltered.length > 0 ? (
              <View>
                {authorProfileBanner}
                {childSections.length > 0 ? (
                  <View style={isAuthorsLeafGrid ? styles.authorsGrid : styles.bentoSubGrid}>
                    {childSections.map((subNode) => renderSectionCard(subNode))}
                  </View>
                ) : null}

                {directBooksFiltered.length > 0 ? (
                  <View style={styles.booksToolbar}>
                    <Text style={[styles.booksToolbarCount, { color: theme.muted, fontSize: fs(12) }]}>
                      {directBooksFiltered.length.toLocaleString()} books
                    </Text>
                    <View style={[styles.viewTogglePill, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
                      {(['grid', 'list'] as const).map((vm) => {
                        const active = viewMode === vm;
                        return (
                          <TouchableOpacity
                            key={vm}
                            style={[styles.viewToggleBtn, active && { backgroundColor: theme.cream }]}
                            onPress={() => setViewMode(vm)}
                            activeOpacity={0.84}
                          >
                            <Text
                              style={[
                                styles.viewToggleText,
                                { color: active ? theme.creamInk : theme.muted, fontSize: fs(11) },
                                active && styles.viewToggleTextActive,
                              ]}
                            >
                              {vm === 'grid' ? 'Grid' : 'List'}
                            </Text>
                          </TouchableOpacity>
                        );
                      })}
                    </View>
                  </View>
                ) : null}
              </View>
            ) : undefined
          }
          ListEmptyComponent={
            childSections.length === 0 ? (
              <View style={styles.emptyBox}>
                <Text style={[styles.emptyText, { color: theme.muted, fontSize: fs(13) }]}>
                  No matching items.
                </Text>
              </View>
            ) : undefined
          }
          renderItem={({ item }) => {
            const offline = offlineById[item.id];
            const dlPct = downloadingMap[item.id];
            if (viewMode === 'grid') {
              return (
                <TouchableOpacity
                  style={styles.gridBookTile}
                  onPress={() => onOpenDetail(item)}
                  activeOpacity={0.86}
                >
                  <BookCover
                    book={item}
                    localCoverUri={offline?.coverLocalUri}
                    width={96}
                    height={140}
                    borderRadius={9}
                    isOffline={Boolean(offline)}
                  />
                  <Text style={[styles.gridBookTitle, { color: theme.ink, fontSize: fs(11.5) }]} numberOfLines={2}>
                    {item.title}
                  </Text>
                  <Text style={[styles.gridBookAuthor, { color: theme.muted, fontSize: fs(10) }]} numberOfLines={1}>
                    {item.author}
                  </Text>
                </TouchableOpacity>
              );
            }
            return (
              <TouchableOpacity
                style={[styles.bookRow, { backgroundColor: theme.surfaceAlt, borderColor: theme.borderSubtle }]}
                onPress={() => onOpenDetail(item)}
                activeOpacity={0.85}
              >
                <BookCover
                  book={item}
                  localCoverUri={offline?.coverLocalUri}
                  width={54}
                  height={80}
                  borderRadius={7}
                  isOffline={Boolean(offline)}
                />
                <View style={styles.bookBody}>
                  <Text style={[styles.bookTitle, { color: theme.ink, fontSize: fs(13) }]} numberOfLines={2}>
                    {item.title}
                  </Text>
                  <Text style={[styles.bookAuthor, { color: theme.muted, fontSize: fs(11) }]} numberOfLines={1}>
                    {item.author} · {item.fmt}
                  </Text>
                  <View style={styles.bookBtns}>
                    <TouchableOpacity
                      style={[styles.readIconPill, { backgroundColor: theme.cream }]}
                      onPress={() => onQuickRead(item)}
                      accessibilityLabel="Read book"
                    >
                      <BookOpenIcon size={15} color={theme.creamInk} />
                      <Text style={[styles.readIconLabel, { color: theme.creamInk, fontSize: fs(11) }]}>
                        {offline ? 'Offline' : 'Read'}
                      </Text>
                    </TouchableOpacity>

                    {offline ? (
                      <View
                        style={[styles.actionIconBtn, { backgroundColor: theme.sage, borderColor: theme.sage }]}
                        accessibilityLabel="Available offline"
                      >
                        <OfflineIcon size={15} color={theme.ink} />
                      </View>
                    ) : dlPct !== undefined ? (
                      <View style={[styles.actionIconBtn, { borderColor: theme.accent }]}>
                        <ActivityIndicator size="small" color={theme.accent} />
                      </View>
                    ) : (
                      <TouchableOpacity
                        style={[styles.actionIconBtn, { borderColor: theme.accent }]}
                        onPress={() => onMakeOffline(item)}
                        accessibilityLabel="Download offline"
                      >
                        <DownloadIcon size={15} color={theme.accent} />
                      </TouchableOpacity>
                    )}
                  </View>
                </View>
              </TouchableOpacity>
            );
          }}
        />
      )}

      <AuthorDetailModal
        visible={authorModalOpen}
        authorName={currentNode.name}
        group={authorDetail?.group || path[1] || 'Authors & Scholars'}
        bookCount={currentNode.totalCount}
        subfolderCount={currentNode.children.size}
        shortDesc={authorDetail?.shortDesc}
        bio={authorDetail?.bio}
        wikiUrl={authorDetail?.wikiUrl}
        onClose={() => setAuthorModalOpen(false)}
      />
    </View>
  );
});

const styles = StyleSheet.create({
  root: { flex: 1 },
  header: {
    paddingHorizontal: 18,
    paddingTop: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
  },
  headerLeft: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  iconCircle: {
    width: 38,
    height: 38,
    borderRadius: 19,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  heading: { fontWeight: '800', flex: 1 },
  headerTotalPill: {
    borderWidth: 1,
    borderRadius: 14,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  headerTotalText: { fontWeight: '800' },
  batchBanner: {
    marginHorizontal: 18,
    marginTop: 10,
    borderWidth: 1,
    borderRadius: 16,
    padding: 11,
    gap: 5,
  },
  batchTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  batchTitle: { fontWeight: '800', flex: 1 },
  batchCancelIcon: { borderWidth: 1, borderRadius: 12, padding: 4 },
  batchCurrentTitle: {},
  batchTrack: { height: 5, borderRadius: 3, overflow: 'hidden' },
  batchFill: { height: '100%', borderRadius: 3 },
  crumbOuter: { marginTop: 10 },
  crumbScroll: { paddingHorizontal: 18, alignItems: 'center', gap: 5 },
  crumbChip: { borderWidth: 1, borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4 },
  crumbText: { fontWeight: '600' },
  crumbTextActive: { fontWeight: '800' },
  searchWrap: { paddingHorizontal: 18, marginTop: 10 },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    borderWidth: 1,
    borderRadius: 14,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  filterInput: { flex: 1, paddingVertical: 4 },
  bentoGridWrap: {
    paddingHorizontal: 18,
    paddingTop: 14,
    paddingBottom: 112,
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    rowGap: 12,
  },
  bentoRootCard: {
    width: '48.2%',
    height: 152,
    borderRadius: 22,
    borderWidth: 1,
    overflow: 'hidden',
    padding: 13,
    justifyContent: 'space-between',
  },
  bentoOrb: {
    position: 'absolute',
    right: -24,
    bottom: -28,
    width: 112,
    height: 112,
    borderRadius: 56,
  },
  bentoTopWrap: {
    zIndex: 2,
    paddingRight: 18,
  },
  bentoIconBadge: {
    width: 32,
    height: 32,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  bentoTitle: {
    fontWeight: '800',
    lineHeight: 19,
    marginTop: 8,
  },
  bentoBottomLeft: {
    zIndex: 2,
    maxWidth: '64%',
  },
  bentoCountPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    borderRadius: 10,
    paddingHorizontal: 8,
    paddingVertical: 3,
    alignSelf: 'flex-start',
  },
  bentoCountText: { fontWeight: '800' },
  bentoCoverCluster: {
    position: 'absolute',
    right: 0,
    bottom: 0,
    width: 78,
    height: 88,
    zIndex: 1,
  },
  bentoCoverBack: {
    position: 'absolute',
    right: 20,
    bottom: -12,
    opacity: 0.78,
    transform: [{ rotate: '4deg' }],
  },
  bentoCoverFront: {
    position: 'absolute',
    right: -6,
    bottom: -10,
    transform: [{ rotate: '14deg' }],
    shadowColor: '#000',
    shadowOpacity: 0.32,
    shadowRadius: 8,
    shadowOffset: { width: -2, height: 4 },
    elevation: 6,
  },
  bentoWatermark: {
    position: 'absolute',
    right: -2,
    bottom: -4,
    opacity: 0.28,
    transform: [{ rotate: '12deg' }],
    zIndex: 1,
  },
  drillContent: { paddingHorizontal: 18, paddingTop: 12, paddingBottom: 112, gap: 9 },
  twoColRow: {
    justifyContent: 'space-between',
    marginBottom: 2,
  },
  authorsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    gap: 10,
    marginBottom: 8,
  },
  authorCard: {
    width: '48.2%',
    borderRadius: 18,
    borderWidth: 1,
    padding: 12,
    alignItems: 'center',
    gap: 7,
  },
  authorCardName: { fontWeight: '700', textAlign: 'center', lineHeight: 17 },
  miniPill: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  miniPillText: { fontWeight: '700' },
  bentoSubGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    rowGap: 10,
    marginBottom: 10,
  },
  bentoSubCard: {
    width: '48.2%',
    minHeight: 110,
    borderRadius: 18,
    borderWidth: 1,
    overflow: 'hidden',
    padding: 12,
    justifyContent: 'space-between',
  },
  bentoSubOrb: {
    position: 'absolute',
    right: -20,
    bottom: -24,
    width: 84,
    height: 84,
    borderRadius: 42,
  },
  bentoSubTitle: {
    fontWeight: '800',
    lineHeight: 17,
    paddingRight: 24,
    zIndex: 2,
  },
  bentoSubBottomLeft: {
    zIndex: 2,
    maxWidth: '70%',
    marginTop: 10,
  },
  bentoSubCover: {
    position: 'absolute',
    right: -5,
    bottom: -8,
    zIndex: 1,
    transform: [{ rotate: '13deg' }],
    shadowColor: '#000',
    shadowOpacity: 0.28,
    shadowRadius: 6,
    shadowOffset: { width: -2, height: 3 },
    elevation: 5,
  },
  bentoSubWatermark: {
    position: 'absolute',
    right: -2,
    bottom: -4,
    opacity: 0.26,
    transform: [{ rotate: '12deg' }],
    zIndex: 1,
  },
  booksToolbar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 2,
    marginBottom: 4,
  },
  booksToolbarCount: { fontWeight: '700' },
  viewTogglePill: {
    flexDirection: 'row',
    borderRadius: 12,
    borderWidth: 1,
    padding: 2,
    gap: 2,
  },
  viewToggleBtn: {
    borderRadius: 9,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  viewToggleText: { fontWeight: '600' },
  viewToggleTextActive: { fontWeight: '800' },
  bookGridRow: {
    justifyContent: 'flex-start',
    gap: 10,
    marginBottom: 6,
  },
  gridBookTile: {
    width: '31%',
    alignItems: 'center',
    gap: 6,
  },
  gridBookTitle: {
    fontWeight: '700',
    lineHeight: 15.5,
    alignSelf: 'stretch',
  },
  gridBookAuthor: {
    alignSelf: 'stretch',
  },
  bookRow: {
    flexDirection: 'row',
    gap: 11,
    borderRadius: 14,
    padding: 10,
    borderWidth: 1,
  },
  bookBody: { flex: 1, justifyContent: 'space-between', gap: 3 },
  bookTitle: { fontWeight: '700', lineHeight: 18 },
  bookAuthor: {},
  bookBtns: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4 },
  readIconPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    borderRadius: 12,
    paddingHorizontal: 11,
    paddingVertical: 5,
  },
  readIconLabel: { fontWeight: '800' },
  actionIconBtn: {
    width: 30,
    height: 30,
    borderRadius: 15,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyBox: { paddingVertical: 40, alignItems: 'center' },
  emptyText: {},
  authorBannerCard: {
    borderRadius: 18,
    borderWidth: 1,
    padding: 13,
    gap: 8,
    marginBottom: 8,
  },
  authorBannerTop: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 11,
  },
  authorBannerInfo: {
    flex: 1,
    gap: 2,
  },
  authorBannerName: {
    fontWeight: '800',
  },
  authorBannerSub: {
    fontWeight: '600',
  },
  authorDetailsBtn: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  authorDetailsBtnText: {
    fontWeight: '800',
  },
  authorBannerBio: {
    lineHeight: 17.5,
  },
});
