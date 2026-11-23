import React, { useMemo, useState } from 'react';
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
import { BookCover } from '../components/BookCover';
import { CategoryIcon } from '../components/CategoryIcon';
import {
  ArrowLeftIcon,
  BookOpenIcon,
  CheckCircleIcon,
  ChevronRightIcon,
  CloseIcon,
  DownloadIcon,
  SearchIcon,
} from '../components/Icons';
import { useAppTheme } from '../context/ThemeContext';
import type { BatchDownloadStatus, Book, OfflineBookEntry } from '../types';

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

function classSortOrder(name: string): number {
  const low = name.toLowerCase();
  if (low.includes('pre-primary')) return 0;
  const m = low.match(/class\s*(\d+)/);
  if (m) return parseInt(m[1], 10);
  return 999;
}

export function ExploreScreen({
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
}: Props) {
  const { theme, fs } = useAppTheme();
  const [filterText, setFilterText] = useState('');

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
        const parts = book.sub.split('/').filter(Boolean);
        let acc = '';
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

  const quickClassChips = useMemo(() => {
    if (path[0] !== 'Education & Textbooks') return [];
    const eduNode = rootTree.children.get('Education & Textbooks');
    const genNode = eduNode?.children.get('General Education');
    if (!genNode) return [];

    const collected: { label: string; path: string[]; count: number }[] = [];
    for (const levelNode of genNode.children.values()) {
      for (const leaf of levelNode.children.values()) {
        if (/^(pre-primary|class\s*\d+)$/i.test(leaf.name) && leaf.totalCount > 0) {
          collected.push({
            label: leaf.name,
            path: ['Education & Textbooks', 'General Education', levelNode.name, leaf.name],
            count: leaf.totalCount,
          });
        }
      }
    }
    collected.sort((a, b) => classSortOrder(a.label) - classSortOrder(b.label));
    return collected;
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
    return path.length >= 2 || childSections.every((c) => c.children.size === 0);
  }, [path, childSections]);

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

          {path[0] === 'Authors & Scholars' && path.length >= 2 ? (
            <AuthorAvatar name={currentNode.name} size={36} />
          ) : !isRoot ? (
            <CategoryIcon name={currentNode.name} size={28} />
          ) : null}

          <Text style={[styles.heading, { color: theme.ink, fontSize: fs(21) }]} numberOfLines={1}>
            {isRoot ? 'CATEGORIES' : currentNode.name}
          </Text>
        </View>

        {!isRoot ? (
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
                <View style={[styles.iconCircle, { backgroundColor: theme.sage, borderColor: theme.sage }]}>
                  <CheckCircleIcon size={18} color={theme.ink} />
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
        ) : null}
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
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.crumbScroll}>
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

      {/* Quick Class 1-12 Chips inside Education & Textbooks */}
      {quickClassChips.length > 0 ? (
        <View style={styles.classChipsOuter}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.classChipsScroll}>
            {quickClassChips.map((ch) => {
              const active = path[path.length - 1] === ch.label;
              return (
                <TouchableOpacity
                  key={ch.label}
                  style={[
                    styles.classChip,
                    {
                      backgroundColor: active ? theme.accent : theme.surface,
                      borderColor: active ? theme.accent : theme.border,
                    },
                  ]}
                  onPress={() => updatePath(ch.path)}
                  activeOpacity={0.82}
                >
                  <Text
                    style={[
                      styles.classChipText,
                      { color: active ? theme.creamInk : theme.ink, fontSize: fs(11.5) },
                    ]}
                  >
                    {ch.label} ({ch.count})
                  </Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>
        </View>
      ) : null}

      {/* Editorial Sleek Category Showcase (Root) OR Subcategories + Books */}
      {isRoot ? (
        <ScrollView contentContainerStyle={styles.rootListWrap} showsVerticalScrollIndicator={false}>
          {childSections.map((node) => (
            <TouchableOpacity
              key={node.name}
              style={[styles.editorialRootCard, { backgroundColor: theme.surface, borderColor: theme.border }]}
              onPress={() => updatePath([node.name])}
              activeOpacity={0.84}
            >
              <View style={[styles.rootIconTile, { backgroundColor: theme.accentSoft }]}>
                <CategoryIcon name={node.name} size={34} />
              </View>

              <View style={styles.rootCenter}>
                <Text style={[styles.rootTitle, { color: theme.ink, fontSize: fs(15) }]} numberOfLines={1}>
                  {node.name}
                </Text>
                <Text style={[styles.rootCount, { color: theme.accent, fontSize: fs(11.5) }]}>
                  {node.totalCount.toLocaleString()} books
                </Text>
              </View>

              {node.previews.length > 0 ? (
                <View style={styles.miniStack}>
                  {node.previews.slice(0, 2).map((pb) => (
                    <BookCover
                      key={pb.id}
                      book={pb}
                      localCoverUri={offlineById[pb.id]?.coverLocalUri}
                      width={28}
                      height={42}
                      borderRadius={4}
                    />
                  ))}
                </View>
              ) : null}

              <ChevronRightIcon size={18} color={theme.muted} />
            </TouchableOpacity>
          ))}
        </ScrollView>
      ) : (
        <FlatList
          data={directBooksFiltered}
          keyExtractor={(item) => item.id}
          initialNumToRender={12}
          windowSize={7}
          contentContainerStyle={styles.drillContent}
          showsVerticalScrollIndicator={false}
          ListHeaderComponent={
            childSections.length > 0 ? (
              isAuthorsLeafGrid ? (
                <View style={styles.authorsGrid}>
                  {childSections.map((subNode) => {
                    const subOffline = countOfflineInNode(subNode, offlineById);
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
                  })}
                </View>
              ) : (
                <View style={styles.subListWrap}>
                  {childSections.map((subNode) => {
                    const subOffline = countOfflineInNode(subNode, offlineById);
                    return (
                      <TouchableOpacity
                        key={subNode.name}
                        style={[styles.editorialSubRow, { backgroundColor: theme.surface, borderColor: theme.border }]}
                        onPress={() => updatePath([...path, subNode.name])}
                        activeOpacity={0.84}
                      >
                        <View style={[styles.subIconTile, { backgroundColor: theme.accentSoft }]}>
                          <CategoryIcon name={subNode.name} size={26} />
                        </View>
                        <View style={styles.subInfo}>
                          <Text
                            style={[styles.subTitle, { color: theme.ink, fontSize: fs(14) }]}
                            numberOfLines={1}
                          >
                            {subNode.name}
                          </Text>
                          <Text style={[styles.subMeta, { color: theme.accent, fontSize: fs(11.5) }]}>
                            {subNode.totalCount.toLocaleString()} books
                            {subOffline > 0 ? ` · ${subOffline} offline` : ''}
                          </Text>
                        </View>
                        {subOffline > 0 ? <CheckCircleIcon size={16} color={theme.sage} /> : null}
                        <ChevronRightIcon size={17} color={theme.muted} />
                      </TouchableOpacity>
                    );
                  })}
                </View>
              )
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
                      <View style={[styles.actionIconBtn, { backgroundColor: theme.sage, borderColor: theme.sage }]}>
                        <CheckCircleIcon size={15} color={theme.ink} />
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
    </View>
  );
}

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
  classChipsOuter: { marginTop: 10 },
  classChipsScroll: { paddingHorizontal: 18, gap: 7 },
  classChip: {
    borderWidth: 1,
    borderRadius: 14,
    paddingHorizontal: 11,
    paddingVertical: 6,
  },
  classChipText: { fontWeight: '700' },
  rootListWrap: {
    paddingHorizontal: 18,
    paddingTop: 12,
    paddingBottom: 112,
    gap: 10,
  },
  editorialRootCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    borderRadius: 20,
    borderWidth: 1,
    padding: 12,
  },
  rootIconTile: {
    width: 52,
    height: 52,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rootCenter: { flex: 1, gap: 3 },
  rootTitle: { fontWeight: '800' },
  rootCount: { fontWeight: '700' },
  miniStack: { flexDirection: 'row', gap: 4 },
  drillContent: { paddingHorizontal: 18, paddingTop: 12, paddingBottom: 112, gap: 9 },
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
  subListWrap: { gap: 9, marginBottom: 8 },
  editorialSubRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    borderRadius: 18,
    borderWidth: 1,
    padding: 11,
  },
  subIconTile: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  subInfo: { flex: 1, gap: 2 },
  subTitle: { fontWeight: '700' },
  subMeta: { fontWeight: '600' },
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
});
