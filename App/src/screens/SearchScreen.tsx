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
import { BookCover } from '../components/BookCover';
import { CategoryIcon } from '../components/CategoryIcon';
import {
  BookOpenIcon,
  BookmarkIcon,
  ChevronRightIcon,
  CloseIcon,
  DownloadIcon,
  LayersIcon,
  OfflineIcon,
  SearchIcon,
} from '../components/Icons';
import { useAppTheme } from '../context/ThemeContext';
import { formatBytes } from '../services/libraryStore';
import type { Book, OfflineBookEntry } from '../types';

type SearchScope = 'all' | 'books' | 'authors' | 'categories';

const BOOK_PAGE_SIZE = 42;

interface AuthorIndexItem {
  key: string;
  name: string;
  path: string[];
  groupLabel: string;
  count: number;
  offlineCount: number;
}

interface CategoryIndexItem {
  key: string;
  label: string;
  parentLabel: string;
  path: string[];
  count: number;
}

interface SeriesIndexItem {
  name: string;
  count: number;
  samplePath: string[];
}

interface Props {
  books: Book[];
  categories: string[];
  offlineById: Record<string, OfflineBookEntry>;
  downloadingMap: Record<string, number>;
  savedIds: string[];
  onOpenDetail: (book: Book) => void;
  onQuickRead: (book: Book) => void;
  onMakeOffline: (book: Book) => void;
  onToggleSave: (bookId: string) => void;
  onSelectPath: (path: string[]) => void;
}

const SCOPE_OPTIONS: { key: SearchScope; label: string }[] = [
  { key: 'all', label: 'Everything' },
  { key: 'books', label: 'Books' },
  { key: 'authors', label: 'Authors' },
  { key: 'categories', label: 'Categories' },
];

export const SearchScreen = React.memo(function SearchScreen({
  books,
  categories,
  offlineById,
  downloadingMap,
  savedIds,
  onOpenDetail,
  onQuickRead,
  onMakeOffline,
  onToggleSave,
  onSelectPath,
}: Props) {
  const { theme, fs } = useAppTheme();
  const [query, setQuery] = useState('');
  const [scope, setScope] = useState<SearchScope>('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');
  const [visibleBookCount, setVisibleBookCount] = useState(BOOK_PAGE_SIZE);

  useEffect(() => {
    setVisibleBookCount(BOOK_PAGE_SIZE);
  }, [query, scope]);

  const savedSet = useMemo(() => new Set(savedIds), [savedIds]);

  const { authorIndex, categoryIndex, seriesIndex } = useMemo(() => {
    const authorMap = new Map<
      string,
      {
        name: string;
        hasDedicatedFolder: boolean;
        path: string[];
        groupLabel: string;
        count: number;
        offlineCount: number;
      }
    >();
    const catMap = new Map<string, CategoryIndexItem>();
    const seriesMap = new Map<string, { count: number; samplePath: string[] }>();

    for (const c of categories) {
      if (c) {
        catMap.set(c, { key: c, label: c, parentLabel: 'Collection', path: [c], count: 0 });
      }
    }

    for (const b of books) {
      const cat = b.cat || '';
      if (cat) {
        const existingCat = catMap.get(cat);
        if (existingCat) {
          existingCat.count += 1;
        } else {
          catMap.set(cat, { key: cat, label: cat, parentLabel: 'Collection', path: [cat], count: 1 });
        }
      }

      if (b.sub) {
        const parts = b.sub.split('/').filter(Boolean);
        for (let i = 0; i < Math.min(parts.length, 2); i++) {
          const subSlice = parts.slice(0, i + 1);
          const subKey = `${cat}/${subSlice.join('/')}`;
          const existingSub = catMap.get(subKey);
          if (existingSub) {
            existingSub.count += 1;
          } else {
            catMap.set(subKey, {
              key: subKey,
              label: subSlice[subSlice.length - 1],
              parentLabel: i === 0 ? cat : `${cat} › ${subSlice[0]}`,
              path: cat ? [cat, ...subSlice] : subSlice,
              count: 1,
            });
          }
        }
      }

      let resolvedAuthor = (b.author || '').trim();
      let dedicatedPath: string[] | null = null;
      let groupLabel = b.cat || 'Author';

      if (b.cat === 'Authors & Scholars' && b.sub) {
        const parts = b.sub.split('/').filter(Boolean);
        if (parts.length >= 2) {
          const topGroup = parts[0];
          if (topGroup === 'Bangladeshi Authors' || topGroup === 'International Authors') {
            resolvedAuthor = parts[1];
            dedicatedPath = ['Authors & Scholars', parts[0], parts[1]];
            groupLabel = topGroup;
          } else if (topGroup === 'Islamic Scholars') {
            if (parts.length >= 3) {
              resolvedAuthor = parts[2];
              dedicatedPath = ['Authors & Scholars', parts[0], parts[1], parts[2]];
            } else {
              resolvedAuthor = parts[1];
              dedicatedPath = ['Authors & Scholars', parts[0], parts[1]];
            }
            groupLabel = 'Islamic Scholars';
          }
        }
      }

      const lowerA = resolvedAuthor.toLowerCase();
      if (resolvedAuthor && lowerA !== 'unknown' && lowerA !== 'unknown author') {
        const aKey = lowerA;
        const acc = authorMap.get(aKey);
        if (!acc) {
          authorMap.set(aKey, {
            name: resolvedAuthor,
            hasDedicatedFolder: Boolean(dedicatedPath),
            path: dedicatedPath || (b.cat ? [b.cat, ...(b.sub ? b.sub.split('/').filter(Boolean).slice(0, 1) : [])] : []),
            groupLabel,
            count: 1,
            offlineCount: offlineById[b.id] ? 1 : 0,
          });
        } else {
          acc.count += 1;
          if (offlineById[b.id]) acc.offlineCount += 1;
          if (dedicatedPath && !acc.hasDedicatedFolder) {
            acc.name = resolvedAuthor;
            acc.hasDedicatedFolder = true;
            acc.path = dedicatedPath;
            acc.groupLabel = groupLabel;
          }
        }
      }

      const ser = (b.series || '').trim();
      if (ser) {
        const sAcc = seriesMap.get(ser);
        if (!sAcc) {
          seriesMap.set(ser, {
            count: 1,
            samplePath: b.cat ? [b.cat, ...(b.sub ? b.sub.split('/').filter(Boolean).slice(0, 2) : [])] : [],
          });
        } else {
          sAcc.count += 1;
        }
      }
    }

    const authorsList: AuthorIndexItem[] = Array.from(authorMap.entries())
      .map(([key, val]) => ({
        key,
        name: val.name,
        path: val.path,
        groupLabel: val.groupLabel,
        count: val.count,
        offlineCount: val.offlineCount,
      }))
      .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));

    const catsList: CategoryIndexItem[] = Array.from(catMap.values()).sort(
      (a, b) => b.count - a.count || a.label.localeCompare(b.label)
    );

    const seriesList: SeriesIndexItem[] = Array.from(seriesMap.entries())
      .map(([name, val]) => ({ name, count: val.count, samplePath: val.samplePath }))
      .sort((a, b) => b.count - a.count);

    return { authorIndex: authorsList, categoryIndex: catsList, seriesIndex: seriesList };
  }, [books, categories, offlineById]);

  const tokens = useMemo(
    () =>
      query
        .trim()
        .toLowerCase()
        .split(/\s+/)
        .filter(Boolean),
    [query]
  );

  const hasQuery = tokens.length > 0;

  const matchedAuthors = useMemo(() => {
    if (!hasQuery) return authorIndex.slice(0, 20);
    return authorIndex
      .filter((a) => {
        const hay = `${a.name} ${a.groupLabel}`.toLowerCase();
        return tokens.every((t) => hay.includes(t));
      })
      .slice(0, scope === 'authors' ? 80 : 18);
  }, [authorIndex, hasQuery, tokens, scope]);

  const matchedCategories = useMemo(() => {
    if (!hasQuery) {
      return categoryIndex.filter((c) => c.path.length === 1);
    }
    return categoryIndex
      .filter((c) => {
        const hay = `${c.label} ${c.parentLabel}`.toLowerCase();
        return tokens.every((t) => hay.includes(t));
      })
      .slice(0, scope === 'categories' ? 80 : 18);
  }, [categoryIndex, hasQuery, tokens, scope]);

  const matchedSeries = useMemo(() => {
    if (!hasQuery) return seriesIndex.slice(0, 14);
    return seriesIndex
      .filter((s) => {
        const hay = s.name.toLowerCase();
        return tokens.every((t) => hay.includes(t));
      })
      .slice(0, 12);
  }, [seriesIndex, hasQuery, tokens]);

  const matchedBooks = useMemo(() => {
    if (!hasQuery) return [];
    const results: Book[] = [];
    for (const b of books) {
      const hay = b.searchBlob;
      if (tokens.every((t) => hay.includes(t))) {
        results.push(b);
      }
    }
    return results;
  }, [books, hasQuery, tokens]);

  const visibleBooks = useMemo(
    () => matchedBooks.slice(0, visibleBookCount),
    [matchedBooks, visibleBookCount]
  );

  const loadMoreBooks = useCallback(() => {
    setVisibleBookCount((prev) =>
      prev < matchedBooks.length ? Math.min(matchedBooks.length, prev + BOOK_PAGE_SIZE) : prev
    );
  }, [matchedBooks.length]);

  const handleOpenAuthor = useCallback(
    (author: AuthorIndexItem) => {
      if (author.path.length > 0 && author.path[0] === 'Authors & Scholars') {
        onSelectPath(author.path);
      } else {
        setQuery(author.name);
        setScope('books');
      }
    },
    [onSelectPath]
  );

  const renderDiscoveryEmptyState = () => (
    <ScrollView
      contentContainerStyle={styles.discoveryContent}
      showsVerticalScrollIndicator={false}
      keyboardShouldPersistTaps="handled"
    >
      <Text style={[styles.sectionEyebrow, { color: theme.accent, fontSize: fs(10.5) }]}>
        FEATURED AUTHORS ({authorIndex.length.toLocaleString()})
      </Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.authorHorizontalRow}
      >
        {matchedAuthors.map((author) => (
          <TouchableOpacity
            key={author.key}
            style={[styles.authorChipCard, { backgroundColor: theme.surface, borderColor: theme.border }]}
            onPress={() => handleOpenAuthor(author)}
            activeOpacity={0.85}
          >
            <AuthorAvatar name={author.name} size={50} />
            <Text style={[styles.authorChipName, { color: theme.ink, fontSize: fs(12) }]} numberOfLines={2}>
              {author.name}
            </Text>
            <Text style={[styles.authorChipCount, { color: theme.accent, fontSize: fs(10.5) }]}>
              {author.count.toLocaleString()} {author.count === 1 ? 'book' : 'books'}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <Text style={[styles.sectionEyebrow, { color: theme.accent, fontSize: fs(10.5), marginTop: 18 }]}>
        CATEGORIES ({matchedCategories.length.toLocaleString()})
      </Text>
      <View style={styles.catGrid}>
        {matchedCategories.map((cat) => (
          <TouchableOpacity
            key={cat.key}
            style={[styles.catTile, { backgroundColor: theme.surface, borderColor: theme.border }]}
            onPress={() => onSelectPath(cat.path)}
            activeOpacity={0.85}
          >
            <CategoryIcon name={cat.label} size={18} />
            <View style={styles.catTileBody}>
              <Text style={[styles.catTileTitle, { color: theme.ink, fontSize: fs(12.5) }]} numberOfLines={1}>
                {cat.label}
              </Text>
              <Text style={[styles.catTileCount, { color: theme.muted, fontSize: fs(10.5) }]}>
                {cat.count.toLocaleString()} books
              </Text>
            </View>
            <ChevronRightIcon size={15} color={theme.muted} />
          </TouchableOpacity>
        ))}
      </View>

      {matchedSeries.length > 0 ? (
        <>
          <Text style={[styles.sectionEyebrow, { color: theme.accent, fontSize: fs(10.5), marginTop: 18 }]}>
            POPULAR SERIES & COLLECTIONS
          </Text>
          <View style={styles.seriesWrap}>
            {matchedSeries.map((ser) => (
              <TouchableOpacity
                key={ser.name}
                style={[styles.seriesPill, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
                onPress={() => {
                  setQuery(ser.name);
                  setScope('all');
                }}
                activeOpacity={0.85}
              >
                <LayersIcon size={13} color={theme.accent} />
                <Text style={[styles.seriesPillText, { color: theme.ink, fontSize: fs(11.5) }]} numberOfLines={1}>
                  {ser.name}
                </Text>
                <Text style={[styles.seriesPillCount, { color: theme.muted, fontSize: fs(10.5) }]}>
                  {ser.count}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </>
      ) : null}
    </ScrollView>
  );

  const renderAuthorsOnlyView = () => (
    <FlatList
      data={matchedAuthors}
      keyExtractor={(item) => item.key}
      numColumns={2}
      columnWrapperStyle={styles.gridRow}
      contentContainerStyle={styles.listContent}
      showsVerticalScrollIndicator={false}
      keyboardShouldPersistTaps="handled"
      ListEmptyComponent={
        <View style={styles.emptyBox}>
          <Text style={[styles.emptyTitle, { color: theme.ink, fontSize: fs(15) }]}>No matching authors</Text>
          <Text style={[styles.emptySub, { color: theme.muted, fontSize: fs(12.5) }]}>
            Try another spelling in Bangla or English.
          </Text>
        </View>
      }
      renderItem={({ item }) => (
        <TouchableOpacity
          style={[styles.authorGridCard, { backgroundColor: theme.surface, borderColor: theme.border }]}
          onPress={() => handleOpenAuthor(item)}
          activeOpacity={0.85}
        >
          <AuthorAvatar name={item.name} size={58} />
          <Text style={[styles.authorGridName, { color: theme.ink, fontSize: fs(13) }]} numberOfLines={2}>
            {item.name}
          </Text>
          <Text style={[styles.authorGridCount, { color: theme.accent, fontSize: fs(11) }]}>
            {item.count.toLocaleString()} {item.count === 1 ? 'book' : 'books'}
          </Text>
          <Text style={[styles.authorGridGroup, { color: theme.muted, fontSize: fs(10) }]} numberOfLines={1}>
            {item.groupLabel}
          </Text>
        </TouchableOpacity>
      )}
    />
  );

  const renderCategoriesOnlyView = () => (
    <FlatList
      data={matchedCategories}
      keyExtractor={(item) => item.key}
      contentContainerStyle={styles.listContent}
      showsVerticalScrollIndicator={false}
      keyboardShouldPersistTaps="handled"
      ListEmptyComponent={
        <View style={styles.emptyBox}>
          <Text style={[styles.emptyTitle, { color: theme.ink, fontSize: fs(15) }]}>No matching categories</Text>
          <Text style={[styles.emptySub, { color: theme.muted, fontSize: fs(12.5) }]}>
            Try another subject, class, or collection keyword.
          </Text>
        </View>
      }
      renderItem={({ item }) => (
        <TouchableOpacity
          style={[styles.catRowCard, { backgroundColor: theme.surface, borderColor: theme.border }]}
          onPress={() => onSelectPath(item.path)}
          activeOpacity={0.85}
        >
          <View style={[styles.catIconBox, { backgroundColor: theme.accentSoft }]}>
            <CategoryIcon name={item.path[0] || item.label} size={20} />
          </View>
          <View style={styles.catRowBody}>
            <Text style={[styles.catRowTitle, { color: theme.ink, fontSize: fs(14) }]} numberOfLines={1}>
              {item.label}
            </Text>
            <Text style={[styles.catRowSub, { color: theme.muted, fontSize: fs(11.5) }]} numberOfLines={1}>
              {item.parentLabel} · {item.count.toLocaleString()} books
            </Text>
          </View>
          <ChevronRightIcon size={16} color={theme.muted} />
        </TouchableOpacity>
      )}
    />
  );

  const renderResultsHeader = () => {
    if (!hasQuery || scope === 'books') return null;

    return (
      <View style={styles.resultsHeaderWrap}>
        {matchedAuthors.length > 0 ? (
          <View style={styles.headerBlock}>
            <Text style={[styles.sectionEyebrow, { color: theme.accent, fontSize: fs(10.5) }]}>
              AUTHORS ({matchedAuthors.length})
            </Text>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.authorHorizontalRow}
              keyboardShouldPersistTaps="handled"
            >
              {matchedAuthors.map((author) => (
                <TouchableOpacity
                  key={author.key}
                  style={[styles.authorMiniChip, { backgroundColor: theme.surface, borderColor: theme.border }]}
                  onPress={() => handleOpenAuthor(author)}
                  activeOpacity={0.85}
                >
                  <AuthorAvatar name={author.name} size={36} />
                  <View style={styles.authorMiniTextWrap}>
                    <Text style={[styles.authorMiniName, { color: theme.ink, fontSize: fs(12) }]} numberOfLines={1}>
                      {author.name}
                    </Text>
                    <Text style={[styles.authorMiniCount, { color: theme.muted, fontSize: fs(10) }]}>
                      {author.count.toLocaleString()} books
                    </Text>
                  </View>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        ) : null}

        {matchedCategories.length > 0 ? (
          <View style={styles.headerBlock}>
            <Text style={[styles.sectionEyebrow, { color: theme.accent, fontSize: fs(10.5) }]}>
              CATEGORIES & FOLDERS ({matchedCategories.length})
            </Text>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.authorHorizontalRow}
              keyboardShouldPersistTaps="handled"
            >
              {matchedCategories.map((cat) => (
                <TouchableOpacity
                  key={cat.key}
                  style={[styles.catQuickChip, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
                  onPress={() => onSelectPath(cat.path)}
                  activeOpacity={0.85}
                >
                  <CategoryIcon name={cat.path[0] || cat.label} size={14} />
                  <Text style={[styles.catQuickLabel, { color: theme.ink, fontSize: fs(11.5) }]} numberOfLines={1}>
                    {cat.label}
                  </Text>
                  <Text style={[styles.catQuickCount, { color: theme.muted, fontSize: fs(10.5) }]}>
                    {cat.count}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        ) : null}

        {matchedSeries.length > 0 ? (
          <View style={styles.headerBlock}>
            <Text style={[styles.sectionEyebrow, { color: theme.accent, fontSize: fs(10.5) }]}>
              SERIES ({matchedSeries.length})
            </Text>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.authorHorizontalRow}
              keyboardShouldPersistTaps="handled"
            >
              {matchedSeries.map((ser) => (
                <TouchableOpacity
                  key={ser.name}
                  style={[styles.catQuickChip, { backgroundColor: theme.accentSoft, borderColor: theme.accent }]}
                  onPress={() => {
                    setQuery(ser.name);
                    setScope('books');
                  }}
                  activeOpacity={0.85}
                >
                  <LayersIcon size={13} color={theme.accent} />
                  <Text style={[styles.catQuickLabel, { color: theme.accent, fontSize: fs(11.5) }]} numberOfLines={1}>
                    {ser.name} ({ser.count})
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        ) : null}

        <View style={styles.booksHeaderRow}>
          <Text style={[styles.sectionEyebrow, { color: theme.accent, fontSize: fs(10.5) }]}>
            MATCHING BOOKS ({matchedBooks.length.toLocaleString()})
          </Text>
        </View>
      </View>
    );
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>
      <View style={[styles.topBar, { borderBottomColor: theme.borderSubtle }]}>
        <View style={styles.titleRow}>
          <View style={styles.titleCol}>
            <Text style={[styles.headerTitle, { color: theme.ink, fontSize: fs(21) }]}>Search</Text>
            <Text style={[styles.headerSub, { color: theme.muted, fontSize: fs(11.5) }]}>
              Books, authors, categories, series & formats
            </Text>
          </View>

          {hasQuery && (scope === 'all' || scope === 'books') ? (
            <TouchableOpacity
              style={[styles.togglePill, { backgroundColor: theme.surface, borderColor: theme.border }]}
              onPress={() => setViewMode((m) => (m === 'grid' ? 'list' : 'grid'))}
            >
              <Text style={[styles.togglePillText, { color: theme.ink, fontSize: fs(11.5) }]}>
                {viewMode === 'grid' ? 'List View' : 'Grid View'}
              </Text>
            </TouchableOpacity>
          ) : null}
        </View>

        <View style={[styles.searchBox, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
          <SearchIcon size={17} color={theme.muted} />
          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder="Search book title, author, category, series…"
            placeholderTextColor={theme.muted}
            style={[styles.searchInput, { color: theme.ink, fontSize: fs(13.5) }]}
            returnKeyType="search"
            autoCapitalize="none"
            autoCorrect={false}
          />
          {query.length > 0 ? (
            <TouchableOpacity onPress={() => setQuery('')} hitSlop={8} accessibilityLabel="Clear search">
              <CloseIcon size={16} color={theme.muted} />
            </TouchableOpacity>
          ) : null}
        </View>

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.scopeRow}
          keyboardShouldPersistTaps="handled"
        >
          {SCOPE_OPTIONS.map((opt) => {
            const active = scope === opt.key;
            return (
              <TouchableOpacity
                key={opt.key}
                style={[
                  styles.scopeChip,
                  {
                    backgroundColor: active ? theme.accentSoft : theme.surfaceAlt,
                    borderColor: active ? theme.accent : theme.borderSubtle,
                  },
                ]}
                onPress={() => setScope(opt.key)}
                activeOpacity={0.85}
              >
                <Text
                  style={[
                    styles.scopeChipText,
                    { color: active ? theme.accent : theme.muted, fontSize: fs(12) },
                  ]}
                >
                  {opt.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>

      {scope === 'authors' ? (
        renderAuthorsOnlyView()
      ) : scope === 'categories' ? (
        renderCategoriesOnlyView()
      ) : !hasQuery ? (
        renderDiscoveryEmptyState()
      ) : (
        <FlatList
          key={`books-${viewMode}`}
          data={visibleBooks}
          keyExtractor={(item) => item.id}
          numColumns={viewMode === 'grid' ? 3 : 1}
          columnWrapperStyle={viewMode === 'grid' ? styles.bookGridRow : undefined}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
          initialNumToRender={12}
          maxToRenderPerBatch={10}
          windowSize={5}
          removeClippedSubviews
          onEndReached={loadMoreBooks}
          onEndReachedThreshold={0.7}
          ListHeaderComponent={hasQuery && scope !== 'books' ? (renderResultsHeader() ?? undefined) : undefined}
          ListEmptyComponent={
            matchedAuthors.length === 0 && matchedCategories.length === 0 ? (
              <View style={styles.emptyBox}>
                <Text style={[styles.emptyTitle, { color: theme.ink, fontSize: fs(16) }]}>
                  Nothing matched "{query.trim()}"
                </Text>
                <Text style={[styles.emptySub, { color: theme.muted, fontSize: fs(12.5) }]}>
                  Try searching by partial book name, author name, subject, or format (PDF, EPUB).
                </Text>
              </View>
            ) : undefined
          }
          renderItem={({ item }) => {
            const offline = offlineById[item.id];
            const dlPct = downloadingMap[item.id];
            const isSaved = savedSet.has(item.id);
            const leafSub = (item.sub || item.cat).split('/').pop() || item.cat;

            if (viewMode === 'grid') {
              return (
                <TouchableOpacity
                  style={styles.bookGridTile}
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
                  <Text style={[styles.bookGridTitle, { color: theme.ink, fontSize: fs(11.5) }]} numberOfLines={2}>
                    {item.title}
                  </Text>
                  <Text style={[styles.bookGridAuthor, { color: theme.muted, fontSize: fs(10) }]} numberOfLines={1}>
                    {item.author}
                  </Text>
                </TouchableOpacity>
              );
            }

            return (
              <TouchableOpacity
                style={[styles.bookRowCard, { backgroundColor: theme.surface, borderColor: theme.border }]}
                onPress={() => onOpenDetail(item)}
                activeOpacity={0.85}
              >
                <BookCover
                  book={item}
                  localCoverUri={offline?.coverLocalUri}
                  width={56}
                  height={84}
                  borderRadius={8}
                  isOffline={Boolean(offline)}
                />

                <View style={styles.bookRowBody}>
                  <Text style={[styles.bookRowTitle, { color: theme.ink, fontSize: fs(13.5) }]} numberOfLines={2}>
                    {item.title}
                  </Text>
                  <Text style={[styles.bookRowAuthor, { color: theme.muted, fontSize: fs(11.5) }]} numberOfLines={1}>
                    {item.author}
                  </Text>
                  <Text style={[styles.bookRowMeta, { color: theme.accent, fontSize: fs(10.5) }]} numberOfLines={1}>
                    {leafSub}
                    {item.series ? ` · ${item.series}` : ''} · {item.fmt} · {formatBytes(item.size)}
                  </Text>

                  <View style={styles.bookRowActions}>
                    <TouchableOpacity
                      style={[styles.readBtn, { backgroundColor: theme.cream }]}
                      onPress={() => onQuickRead(item)}
                      activeOpacity={0.85}
                    >
                      <BookOpenIcon size={14} color={theme.creamInk} />
                      <Text style={[styles.readBtnText, { color: theme.creamInk, fontSize: fs(11.5) }]}>
                        {offline ? 'Offline' : 'Read'}
                      </Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={[
                        styles.actionCircle,
                        {
                          borderColor: isSaved ? theme.accent : theme.border,
                          backgroundColor: isSaved ? theme.accentSoft : 'transparent',
                        },
                      ]}
                      onPress={() => onToggleSave(item.id)}
                      accessibilityLabel={isSaved ? 'Remove bookmark' : 'Bookmark book'}
                    >
                      <BookmarkIcon size={15} color={theme.accent} filled={isSaved} />
                    </TouchableOpacity>

                    {offline ? (
                      <View
                        style={[styles.actionCircle, { backgroundColor: theme.sage, borderColor: theme.sage }]}
                        accessibilityLabel="Available offline"
                      >
                        <OfflineIcon size={15} color={theme.ink} />
                      </View>
                    ) : dlPct !== undefined ? (
                      <View style={[styles.actionCircle, { borderColor: theme.accent }]}>
                        <ActivityIndicator size="small" color={theme.accent} />
                      </View>
                    ) : (
                      <TouchableOpacity
                        style={[styles.actionCircle, { borderColor: theme.border }]}
                        onPress={() => onMakeOffline(item)}
                        accessibilityLabel="Save book offline"
                      >
                        <DownloadIcon size={15} color={theme.muted} />
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
});

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  topBar: {
    paddingHorizontal: 18,
    paddingTop: 10,
    paddingBottom: 10,
    borderBottomWidth: 1,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  titleCol: {
    flex: 1,
    paddingRight: 10,
  },
  headerTitle: {
    fontWeight: '800',
    letterSpacing: -0.3,
  },
  headerSub: {
    marginTop: 2,
    fontWeight: '500',
  },
  togglePill: {
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  togglePillText: {
    fontWeight: '700',
  },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 12,
    borderWidth: 1,
    paddingHorizontal: 12,
    height: 44,
    gap: 8,
  },
  searchInput: {
    flex: 1,
    fontWeight: '500',
    paddingVertical: 6,
  },
  scopeRow: {
    flexDirection: 'row',
    gap: 8,
    paddingTop: 10,
  },
  scopeChip: {
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 13,
    paddingVertical: 6,
  },
  scopeChipText: {
    fontWeight: '700',
  },
  discoveryContent: {
    paddingHorizontal: 18,
    paddingTop: 14,
    paddingBottom: 120,
  },
  sectionEyebrow: {
    fontWeight: '800',
    letterSpacing: 1.0,
    marginBottom: 8,
  },
  authorHorizontalRow: {
    flexDirection: 'row',
    gap: 10,
    paddingBottom: 4,
  },
  authorChipCard: {
    width: 112,
    borderRadius: 14,
    borderWidth: 1,
    paddingVertical: 12,
    paddingHorizontal: 8,
    alignItems: 'center',
  },
  authorChipName: {
    fontWeight: '700',
    textAlign: 'center',
    marginTop: 8,
  },
  authorChipCount: {
    fontWeight: '700',
    marginTop: 3,
  },
  catGrid: {
    gap: 8,
  },
  catTile: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    borderRadius: 13,
    borderWidth: 1,
    paddingHorizontal: 13,
    paddingVertical: 11,
  },
  catTileBody: {
    flex: 1,
  },
  catTileTitle: {
    fontWeight: '700',
  },
  catTileCount: {
    marginTop: 2,
    fontWeight: '500',
  },
  seriesWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  seriesPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 7,
    maxWidth: '100%',
  },
  seriesPillText: {
    fontWeight: '700',
    maxWidth: 210,
  },
  seriesPillCount: {
    fontWeight: '600',
  },
  listContent: {
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 120,
  },
  gridRow: {
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  authorGridCard: {
    width: '48.5%',
    borderRadius: 14,
    borderWidth: 1,
    paddingVertical: 14,
    paddingHorizontal: 10,
    alignItems: 'center',
  },
  authorGridName: {
    fontWeight: '700',
    textAlign: 'center',
    marginTop: 9,
  },
  authorGridCount: {
    fontWeight: '700',
    marginTop: 4,
  },
  authorGridGroup: {
    marginTop: 2,
    fontWeight: '500',
  },
  catRowCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    borderRadius: 13,
    borderWidth: 1,
    padding: 12,
    marginBottom: 8,
  },
  catIconBox: {
    width: 38,
    height: 38,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  catRowBody: {
    flex: 1,
  },
  catRowTitle: {
    fontWeight: '700',
  },
  catRowSub: {
    marginTop: 2,
    fontWeight: '500',
  },
  resultsHeaderWrap: {
    marginBottom: 4,
  },
  headerBlock: {
    marginBottom: 14,
  },
  booksHeaderRow: {
    marginBottom: 4,
  },
  authorMiniChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 9,
    borderRadius: 12,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 8,
    maxWidth: 220,
  },
  authorMiniTextWrap: {
    flexShrink: 1,
  },
  authorMiniName: {
    fontWeight: '700',
  },
  authorMiniCount: {
    fontWeight: '500',
    marginTop: 1,
  },
  catQuickChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  catQuickLabel: {
    fontWeight: '700',
    maxWidth: 180,
  },
  catQuickCount: {
    fontWeight: '600',
  },
  bookGridRow: {
    justifyContent: 'space-between',
    marginBottom: 14,
  },
  bookGridTile: {
    width: '31.5%',
    alignItems: 'center',
  },
  bookGridTitle: {
    fontWeight: '700',
    marginTop: 6,
    textAlign: 'center',
  },
  bookGridAuthor: {
    marginTop: 2,
    textAlign: 'center',
  },
  bookRowCard: {
    flexDirection: 'row',
    gap: 12,
    borderRadius: 14,
    borderWidth: 1,
    padding: 11,
    marginBottom: 10,
  },
  bookRowBody: {
    flex: 1,
    justifyContent: 'space-between',
  },
  bookRowTitle: {
    fontWeight: '700',
  },
  bookRowAuthor: {
    marginTop: 2,
    fontWeight: '500',
  },
  bookRowMeta: {
    marginTop: 3,
    fontWeight: '700',
  },
  bookRowActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 8,
  },
  readBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  readBtnText: {
    fontWeight: '800',
  },
  actionCircle: {
    width: 30,
    height: 30,
    borderRadius: 15,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyBox: {
    alignItems: 'center',
    paddingVertical: 48,
    paddingHorizontal: 24,
  },
  emptyTitle: {
    fontWeight: '700',
    textAlign: 'center',
  },
  emptySub: {
    marginTop: 6,
    textAlign: 'center',
    lineHeight: 19,
  },
});
