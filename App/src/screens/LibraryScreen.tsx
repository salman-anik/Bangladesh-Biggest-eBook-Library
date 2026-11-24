import React, { useEffect, useMemo, useState } from 'react';
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

import { BookCover } from '../components/BookCover';
import {
  BookOpenIcon,
  BookmarkIcon,
  CheckCircleIcon,
  CloseIcon,
  DownloadIcon,
  SearchIcon,
  TrashIcon,
} from '../components/Icons';
import { useAppTheme } from '../context/ThemeContext';
import { formatBytes } from '../services/libraryStore';
import type { Book, BookProgress, OfflineBookEntry } from '../types';

type ShelfTabKey = 'reading' | 'saved' | 'offline';

interface Props {
  books: Book[];
  categories: string[];
  currentlyReading: Book | null | undefined;
  progressById: Record<string, BookProgress>;
  savedIds: string[];
  offlineById: Record<string, OfflineBookEntry>;
  downloadingMap: Record<string, number>;
  initialCategory?: string;
  initialSubcategory?: string;
  onClearSubcategory?: () => void;
  onOpenDetail: (book: Book) => void;
  onQuickRead: (book: Book) => void;
  onMakeOffline: (book: Book) => void;
  onToggleSave: (bookId: string) => void;
  onRemoveOffline: (bookId: string) => void;
  onRemoveFromReading: (bookId: string) => void;
  onExploreCategories: () => void;
}

export function LibraryScreen({
  books,
  currentlyReading,
  progressById,
  savedIds,
  offlineById,
  downloadingMap,
  initialCategory = '',
  initialSubcategory = '',
  onClearSubcategory,
  onOpenDetail,
  onQuickRead,
  onMakeOffline,
  onToggleSave,
  onRemoveOffline,
  onRemoveFromReading,
  onExploreCategories,
}: Props) {
  const { theme, fs } = useAppTheme();
  const [query, setQuery] = useState('');
  const [shelfTab, setShelfTab] = useState<ShelfTabKey>('reading');
  const [searchViewMode, setSearchViewMode] = useState<'grid' | 'list'>('grid');
  const [catFilter, setCatFilter] = useState<string>(initialCategory || '');
  const [subFilter, setSubFilter] = useState<string>(initialSubcategory || '');

  useEffect(() => {
    setCatFilter(initialCategory || '');
    setSubFilter(initialSubcategory || '');
  }, [initialCategory, initialSubcategory]);

  const booksById = useMemo(() => {
    const map = new Map<string, Book>();
    for (const b of books) map.set(b.id, b);
    return map;
  }, [books]);

  const savedSet = useMemo(() => new Set(savedIds), [savedIds]);

  const readingItems = useMemo(() => {
    const seen = new Set<string>();
    const list: { book: Book; progress?: BookProgress }[] = [];

    const tracked = Object.values(progressById).sort((a, b) =>
      (b.updatedAt || '').localeCompare(a.updatedAt || '')
    );
    for (const prog of tracked) {
      const b = booksById.get(prog.bookId);
      if (b && !seen.has(b.id)) {
        seen.add(b.id);
        list.push({ book: b, progress: prog });
      }
    }

    if (currentlyReading && !seen.has(currentlyReading.id)) {
      seen.add(currentlyReading.id);
      list.push({ book: currentlyReading, progress: progressById[currentlyReading.id] });
    }

    return list;
  }, [progressById, booksById, currentlyReading]);

  const savedBooks = useMemo(() => {
    const list: Book[] = [];
    for (let i = savedIds.length - 1; i >= 0; i--) {
      const b = booksById.get(savedIds[i]);
      if (b) list.push(b);
    }
    return list;
  }, [savedIds, booksById]);

  const offlineItems = useMemo(() => {
    const entries = Object.values(offlineById).sort((a, b) =>
      (b.downloadedAt || '').localeCompare(a.downloadedAt || '')
    );
    return entries.map((entry) => {
      const book = booksById.get(entry.bookId) || {
        id: entry.bookId,
        title: entry.title,
        author: entry.author,
        cat: entry.cat,
        sub: entry.sub,
        lang: 'Unknown',
        fmt: entry.fmt,
        size: entry.size,
        coverId: '',
        series: '',
        searchBlob: '',
      };
      return { book, entry };
    });
  }, [offlineById, booksById]);

  const totalOfflineBytes = useMemo(
    () => offlineItems.reduce((sum, item) => sum + (item.entry.size || 0), 0),
    [offlineItems]
  );

  const isSearchMode = Boolean(query.trim() || subFilter || catFilter);

  const searchResults = useMemo(() => {
    if (!isSearchMode) return [];
    const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    return books.filter((b) => {
      if (catFilter && b.cat !== catFilter) return false;
      if (subFilter && b.sub !== subFilter && !b.sub.startsWith(subFilter + '/')) return false;
      for (const t of terms) {
        if (!b.searchBlob.includes(t)) return false;
      }
      return true;
    });
  }, [isSearchMode, books, query, catFilter, subFilter]);

  const clearSearchMode = () => {
    setQuery('');
    setCatFilter('');
    setSubFilter('');
    onClearSubcategory?.();
  };

  const heroProg = currentlyReading ? progressById[currentlyReading.id] : undefined;
  const heroPct = heroProg ? Math.min(100, Math.max(0, Math.round(heroProg.progressPct))) : 0;
  const isHeroSaved = currentlyReading ? savedSet.has(currentlyReading.id) : false;

  const activeFilterLabel = subFilter || catFilter;

  return (
    <View style={[styles.root, { backgroundColor: theme.bg }]}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.ink, fontSize: fs(23) }]}>My Shelf</Text>
        <View style={[styles.summaryPill, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
          <Text style={[styles.summaryPillText, { color: theme.accent, fontSize: fs(11.5) }]}>
            {savedBooks.length} saved · {offlineItems.length} offline
          </Text>
        </View>
      </View>

      {/* Instant Search Box */}
      <View style={styles.searchWrap}>
        <View style={[styles.searchBox, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
          <SearchIcon size={16} color={theme.muted} />
          <TextInput
            style={[styles.searchInput, { color: theme.ink, fontSize: fs(13) }]}
            placeholder={`Search shelf or all ${books.length.toLocaleString()} books…`}
            placeholderTextColor={theme.muted}
            value={query}
            onChangeText={setQuery}
          />
          {isSearchMode ? (
            <TouchableOpacity onPress={clearSearchMode} accessibilityLabel="Clear search">
              <CloseIcon size={16} color={theme.muted} />
            </TouchableOpacity>
          ) : null}
        </View>
      </View>

      {isSearchMode ? (
        <>
          <View style={[styles.searchBarBanner, { backgroundColor: theme.accentSoft, borderColor: theme.accent }]}>
            <Text style={[styles.searchBannerText, { color: theme.ink, fontSize: fs(12) }]} numberOfLines={1}>
              {activeFilterLabel ? `${activeFilterLabel} · ` : ''}
              {searchResults.length.toLocaleString()} results
            </Text>
            <View style={styles.searchBannerRight}>
              <View style={[styles.viewTogglePill, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
                {(['grid', 'list'] as const).map((vm) => {
                  const active = searchViewMode === vm;
                  return (
                    <TouchableOpacity
                      key={vm}
                      style={[styles.viewToggleBtn, active && { backgroundColor: theme.cream }]}
                      onPress={() => setSearchViewMode(vm)}
                      activeOpacity={0.84}
                    >
                      <Text
                        style={[
                          styles.viewToggleText,
                          { color: active ? theme.creamInk : theme.muted, fontSize: fs(10.5) },
                          active && styles.viewToggleTextActive,
                        ]}
                      >
                        {vm === 'grid' ? 'Grid' : 'List'}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
              <TouchableOpacity
                style={[styles.backShelfBtn, { backgroundColor: theme.surface, borderColor: theme.border }]}
                onPress={clearSearchMode}
                activeOpacity={0.82}
              >
                <Text style={[styles.backShelfText, { color: theme.cream, fontSize: fs(10.5) }]}>
                  Shelf
                </Text>
              </TouchableOpacity>
            </View>
          </View>

          <FlatList
            key={searchViewMode === 'grid' ? 'search-grid-3' : 'search-list-1'}
            numColumns={searchViewMode === 'grid' ? 3 : 1}
            columnWrapperStyle={searchViewMode === 'grid' ? styles.searchGridRow : undefined}
            data={searchResults}
            keyExtractor={(item) => item.id}
            initialNumToRender={12}
            maxToRenderPerBatch={14}
            windowSize={7}
            contentContainerStyle={styles.listContent}
            showsVerticalScrollIndicator={false}
            ListEmptyComponent={
              <View style={styles.emptyBox}>
                <Text style={[styles.emptyTitle, { color: theme.ink, fontSize: fs(16) }]}>No matching books</Text>
                <Text style={[styles.emptySub, { color: theme.muted, fontSize: fs(12.5) }]}>
                  Try a different keyword or return to My Shelf.
                </Text>
              </View>
            }
            renderItem={({ item }) => {
              const offline = offlineById[item.id];
              const dlPct = downloadingMap[item.id];
              const isSaved = savedSet.has(item.id);
              const leafSub = (item.sub || item.cat).split('/').pop() || item.cat;

              if (searchViewMode === 'grid') {
                return (
                  <TouchableOpacity
                    style={styles.searchGridTile}
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
                    <Text style={[styles.searchGridTitle, { color: theme.ink, fontSize: fs(11.5) }]} numberOfLines={2}>
                      {item.title}
                    </Text>
                    <Text style={[styles.searchGridAuthor, { color: theme.muted, fontSize: fs(10) }]} numberOfLines={1}>
                      {item.author}
                    </Text>
                  </TouchableOpacity>
                );
              }

              return (
                <TouchableOpacity
                  style={[styles.searchCard, { backgroundColor: theme.surface, borderColor: theme.border }]}
                  onPress={() => onOpenDetail(item)}
                  activeOpacity={0.85}
                >
                  <BookCover
                    book={item}
                    localCoverUri={offline?.coverLocalUri}
                    width={58}
                    height={86}
                    borderRadius={8}
                    isOffline={Boolean(offline)}
                  />

                  <View style={styles.cardBody}>
                    <Text style={[styles.bookTitle, { color: theme.ink, fontSize: fs(13.5) }]} numberOfLines={2}>
                      {item.title}
                    </Text>
                    <Text style={[styles.bookAuthor, { color: theme.muted, fontSize: fs(11.5) }]} numberOfLines={1}>
                      {item.author}
                    </Text>
                    <Text style={[styles.bookMeta, { color: theme.accent, fontSize: fs(10.5) }]} numberOfLines={1}>
                      {leafSub} · {item.fmt} · {formatBytes(item.size)}
                    </Text>

                    <View style={styles.cardActions}>
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
                        <View style={[styles.actionCircle, { backgroundColor: theme.sage, borderColor: theme.sage }]}>
                          <CheckCircleIcon size={15} color={theme.ink} />
                        </View>
                      ) : dlPct !== undefined ? (
                        <View style={[styles.actionCircle, { borderColor: theme.accent }]}>
                          <ActivityIndicator size="small" color={theme.accent} />
                        </View>
                      ) : (
                        <TouchableOpacity
                          style={[styles.actionCircle, { borderColor: theme.accent }]}
                          onPress={() => onMakeOffline(item)}
                          activeOpacity={0.85}
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
        </>
      ) : (
        <ScrollView contentContainerStyle={styles.shelfScroll} showsVerticalScrollIndicator={false}>
          {/* Currently Reading Hero Card */}
          {currentlyReading ? (
            <TouchableOpacity
              style={[styles.heroCard, { backgroundColor: theme.surface, borderColor: theme.border }]}
              onPress={() => onOpenDetail(currentlyReading)}
              activeOpacity={0.88}
            >
              <View style={styles.heroTopRow}>
                <View style={[styles.heroBadge, { backgroundColor: theme.accentSoft }]}>
                  <Text style={[styles.heroBadgeText, { color: theme.accent, fontSize: fs(10) }]}>
                    CURRENTLY READING
                  </Text>
                </View>

                <View style={styles.heroHeaderBtns}>
                  <TouchableOpacity
                    style={[
                      styles.heroBookmarkBtn,
                      {
                        backgroundColor: isHeroSaved ? theme.accentSoft : theme.surfaceAlt,
                        borderColor: isHeroSaved ? theme.accent : theme.border,
                      },
                    ]}
                    onPress={() => onToggleSave(currentlyReading.id)}
                    accessibilityLabel={isHeroSaved ? 'Remove from saved' : 'Save book'}
                  >
                    <BookmarkIcon size={15} color={isHeroSaved ? theme.accent : theme.muted} filled={isHeroSaved} />
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[
                      styles.heroBookmarkBtn,
                      { backgroundColor: theme.surfaceAlt, borderColor: theme.border },
                    ]}
                    onPress={() => onRemoveFromReading(currentlyReading.id)}
                    accessibilityLabel="Remove from Continue Reading"
                  >
                    <CloseIcon size={14} color={theme.muted} />
                  </TouchableOpacity>
                </View>
              </View>

              <View style={styles.heroBodyRow}>
                <BookCover
                  book={currentlyReading}
                  localCoverUri={offlineById[currentlyReading.id]?.coverLocalUri}
                  width={68}
                  height={100}
                  borderRadius={9}
                  isOffline={Boolean(offlineById[currentlyReading.id])}
                />

                <View style={styles.heroInfo}>
                  <Text style={[styles.heroTitle, { color: theme.ink, fontSize: fs(15.5) }]} numberOfLines={2}>
                    {currentlyReading.title}
                  </Text>
                  <Text style={[styles.heroAuthor, { color: theme.muted, fontSize: fs(12) }]} numberOfLines={1}>
                    {currentlyReading.author}
                  </Text>

                  <View style={styles.heroProgWrap}>
                    <View style={styles.heroProgMeta}>
                      <Text style={[styles.heroProgLabel, { color: theme.accent, fontSize: fs(11) }]}>
                        {heroPct}%
                      </Text>
                      <Text style={[styles.heroProgPages, { color: theme.muted, fontSize: fs(11) }]}>
                        {heroProg && heroProg.totalPages > 0
                          ? `Page ${heroProg.currentPage} of ${heroProg.totalPages}`
                          : 'Ready to read'}
                      </Text>
                    </View>
                    <View style={[styles.progTrack, { backgroundColor: theme.surfaceAlt }]}>
                      <View
                        style={[
                          styles.progFill,
                          { width: `${Math.max(heroPct > 0 ? 5 : 2, heroPct)}%`, backgroundColor: theme.accent },
                        ]}
                      />
                    </View>
                  </View>

                  <TouchableOpacity
                    style={[styles.continueBtn, { backgroundColor: theme.cream }]}
                    onPress={() => onQuickRead(currentlyReading)}
                    activeOpacity={0.86}
                  >
                    <BookOpenIcon size={15} color={theme.creamInk} />
                    <Text style={[styles.continueBtnText, { color: theme.creamInk, fontSize: fs(12) }]}>
                      Continue Reading
                    </Text>
                  </TouchableOpacity>
                </View>
              </View>
            </TouchableOpacity>
          ) : null}

          {/* 3-Tab Segmented Control: Reading | Saved | Offline */}
          <View style={[styles.segmentedBar, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
            {(
              [
                { key: 'reading', label: 'Reading', count: readingItems.length },
                { key: 'saved', label: 'Saved', count: savedBooks.length },
                { key: 'offline', label: 'Offline', count: offlineItems.length },
              ] as { key: ShelfTabKey; label: string; count: number }[]
            ).map((tab) => {
              const active = shelfTab === tab.key;
              return (
                <TouchableOpacity
                  key={tab.key}
                  style={[
                    styles.segItem,
                    active && { backgroundColor: theme.cream },
                  ]}
                  onPress={() => setShelfTab(tab.key)}
                  activeOpacity={0.85}
                >
                  <Text
                    style={[
                      styles.segText,
                      { color: active ? theme.creamInk : theme.muted, fontSize: fs(12) },
                      active && styles.segTextActive,
                    ]}
                    numberOfLines={1}
                  >
                    {tab.label} ({tab.count})
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          {/* Reading Tab */}
          {shelfTab === 'reading' ? (
            <View style={styles.sectionBlock}>
              {readingItems.length > 0 ? (
                readingItems.map(({ book, progress }) => {
                  const pct = progress ? Math.min(100, Math.max(0, Math.round(progress.progressPct))) : 0;
                  const offline = offlineById[book.id];
                  return (
                    <TouchableOpacity
                      key={book.id}
                      style={[styles.shelfRowCard, { backgroundColor: theme.surface, borderColor: theme.border }]}
                      onPress={() => onOpenDetail(book)}
                      activeOpacity={0.85}
                    >
                      <BookCover
                        book={book}
                        localCoverUri={offline?.coverLocalUri}
                        width={52}
                        height={76}
                        borderRadius={7}
                        isOffline={Boolean(offline)}
                      />

                      <View style={styles.shelfRowBody}>
                        <Text style={[styles.bookTitle, { color: theme.ink, fontSize: fs(13.5) }]} numberOfLines={2}>
                          {book.title}
                        </Text>
                        <Text style={[styles.bookAuthor, { color: theme.muted, fontSize: fs(11.5) }]} numberOfLines={1}>
                          {book.author}
                        </Text>
                        <View style={styles.rowProgWrap}>
                          <View style={[styles.progTrack, { flex: 1, backgroundColor: theme.surfaceAlt }]}>
                            <View
                              style={[
                                styles.progFill,
                                { width: `${Math.max(pct > 0 ? 5 : 2, pct)}%`, backgroundColor: theme.accent },
                              ]}
                            />
                          </View>
                          <Text style={[styles.rowPctText, { color: theme.accent, fontSize: fs(11) }]}>
                            {pct}%
                          </Text>
                        </View>
                      </View>

                      <View style={styles.readingRowActions}>
                        <TouchableOpacity
                          style={[styles.pillCta, { backgroundColor: theme.accentSoft, borderColor: theme.accent }]}
                          onPress={() => onQuickRead(book)}
                          activeOpacity={0.84}
                        >
                          <Text style={[styles.pillCtaText, { color: theme.accent, fontSize: fs(11.5) }]}>
                            Continue
                          </Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                          style={[styles.readingRemoveBtn, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
                          onPress={() => onRemoveFromReading(book.id)}
                          accessibilityLabel="Remove from reading list"
                        >
                          <CloseIcon size={13} color={theme.muted} />
                        </TouchableOpacity>
                      </View>
                    </TouchableOpacity>
                  );
                })
              ) : (
                <View style={[styles.emptyShelfCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
                  <Text style={[styles.emptyTitle, { color: theme.ink, fontSize: fs(15) }]}>
                    Start your reading list
                  </Text>
                  <Text style={[styles.emptySub, { color: theme.muted, fontSize: fs(12) }]}>
                    Open any book to track reading progress automatically.
                  </Text>
                  <TouchableOpacity
                    style={[styles.ctaBtn, { backgroundColor: theme.cream }]}
                    onPress={onExploreCategories}
                  >
                    <Text style={[styles.ctaBtnText, { color: theme.creamInk, fontSize: fs(12) }]}>
                      Explore Categories
                    </Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          ) : null}

          {/* Saved Tab — 2-Column Visual Book Cover Grid */}
          {shelfTab === 'saved' ? (
            savedBooks.length > 0 ? (
              <View style={styles.savedGrid}>
                {savedBooks.map((sb) => {
                  const offline = offlineById[sb.id];
                  return (
                    <TouchableOpacity
                      key={sb.id}
                      style={[styles.savedCard, { backgroundColor: theme.surface, borderColor: theme.border }]}
                      onPress={() => onOpenDetail(sb)}
                      activeOpacity={0.86}
                    >
                      <View style={styles.savedCoverCenter}>
                        <BookCover
                          book={sb}
                          localCoverUri={offline?.coverLocalUri}
                          width={94}
                          height={136}
                          borderRadius={9}
                          isOffline={Boolean(offline)}
                        />
                      </View>
                      <Text style={[styles.savedBookTitle, { color: theme.ink, fontSize: fs(12.5) }]} numberOfLines={2}>
                        {sb.title}
                      </Text>
                      <Text style={[styles.savedBookAuthor, { color: theme.muted, fontSize: fs(11) }]} numberOfLines={1}>
                        {sb.author}
                      </Text>

                      <View style={styles.savedActions}>
                        <TouchableOpacity
                          style={[styles.savedReadBtn, { backgroundColor: theme.cream }]}
                          onPress={() => onQuickRead(sb)}
                          activeOpacity={0.85}
                        >
                          <BookOpenIcon size={13} color={theme.creamInk} />
                          <Text style={[styles.savedReadText, { color: theme.creamInk, fontSize: fs(11) }]}>
                            Read
                          </Text>
                        </TouchableOpacity>

                        <TouchableOpacity
                          style={[styles.savedRemovePill, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
                          onPress={() => onToggleSave(sb.id)}
                          activeOpacity={0.82}
                        >
                          <Text style={[styles.savedRemoveText, { color: theme.muted, fontSize: fs(10.5) }]}>
                            Remove
                          </Text>
                        </TouchableOpacity>
                      </View>
                    </TouchableOpacity>
                  );
                })}
              </View>
            ) : (
              <View style={[styles.emptyShelfCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
                <BookmarkIcon size={28} color={theme.accent} />
                <Text style={[styles.emptyTitle, { color: theme.ink, fontSize: fs(15.5) }]}>No saved books yet</Text>
                <Text style={[styles.emptySub, { color: theme.muted, fontSize: fs(12) }]}>
                  Bookmark any book while browsing to keep it on your personal shelf.
                </Text>
                <TouchableOpacity
                  style={[styles.ctaBtn, { backgroundColor: theme.cream }]}
                  onPress={onExploreCategories}
                  activeOpacity={0.85}
                >
                  <Text style={[styles.ctaBtnText, { color: theme.creamInk, fontSize: fs(12) }]}>
                    Explore Categories
                  </Text>
                </TouchableOpacity>
              </View>
            )
          ) : null}

          {/* Offline Tab — Storage Meter + Downloaded Books */}
          {shelfTab === 'offline' ? (
            <View style={styles.sectionBlock}>
              <View style={[styles.storageBanner, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
                <View style={styles.storageTop}>
                  <Text style={[styles.storageTitle, { color: theme.ink, fontSize: fs(12.5) }]}>
                    Device Storage
                  </Text>
                  <Text style={[styles.storageMeta, { color: theme.accent, fontSize: fs(12) }]}>
                    {offlineItems.length} books downloaded · {formatBytes(totalOfflineBytes)} used on device
                  </Text>
                </View>
                <View style={[styles.progTrack, { backgroundColor: theme.surface }]}>
                  <View
                    style={[
                      styles.progFill,
                      {
                        width: `${offlineItems.length > 0 ? Math.min(100, Math.max(8, offlineItems.length * 6)) : 0}%`,
                        backgroundColor: theme.sage,
                      },
                    ]}
                  />
                </View>
              </View>

              {offlineItems.length > 0 ? (
                offlineItems.map(({ book, entry }) => (
                  <TouchableOpacity
                    key={book.id}
                    style={[styles.shelfRowCard, { backgroundColor: theme.surface, borderColor: theme.border }]}
                    onPress={() => onOpenDetail(book)}
                    activeOpacity={0.85}
                  >
                    <BookCover
                      book={book}
                      localCoverUri={entry.coverLocalUri}
                      width={52}
                      height={76}
                      borderRadius={7}
                      isOffline
                    />

                    <View style={styles.shelfRowBody}>
                      <Text style={[styles.bookTitle, { color: theme.ink, fontSize: fs(13.5) }]} numberOfLines={2}>
                        {book.title}
                      </Text>
                      <Text style={[styles.bookAuthor, { color: theme.muted, fontSize: fs(11.5) }]} numberOfLines={1}>
                        {book.author}
                      </Text>
                      <Text style={[styles.bookMeta, { color: theme.accent, fontSize: fs(10.5) }]} numberOfLines={1}>
                        {book.fmt} · {formatBytes(entry.size)}
                      </Text>

                      <View style={styles.offlineBtnsRow}>
                        <TouchableOpacity
                          style={[styles.readOfflinePill, { backgroundColor: theme.cream }]}
                          onPress={() => onQuickRead(book)}
                          activeOpacity={0.85}
                        >
                          <BookOpenIcon size={13} color={theme.creamInk} />
                          <Text style={[styles.readBtnText, { color: theme.creamInk, fontSize: fs(11) }]}>
                            Read Offline
                          </Text>
                        </TouchableOpacity>

                        <TouchableOpacity
                          style={[styles.removeOfflineBtn, { borderColor: theme.border, backgroundColor: theme.surfaceAlt }]}
                          onPress={() => onRemoveOffline(book.id)}
                          activeOpacity={0.82}
                          accessibilityLabel="Remove offline copy"
                        >
                          <TrashIcon size={13} color={theme.danger} />
                          <Text style={[styles.removeOfflineText, { color: theme.danger, fontSize: fs(11) }]}>
                            Remove
                          </Text>
                        </TouchableOpacity>
                      </View>
                    </View>
                  </TouchableOpacity>
                ))
              ) : (
                <View style={[styles.emptyShelfCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
                  <DownloadIcon size={28} color={theme.accent} />
                  <Text style={[styles.emptyTitle, { color: theme.ink, fontSize: fs(15.5) }]}>
                    No offline books yet
                  </Text>
                  <Text style={[styles.emptySub, { color: theme.muted, fontSize: fs(12) }]}>
                    Download books or full categories for instant offline reading anywhere.
                  </Text>
                  <TouchableOpacity
                    style={[styles.ctaBtn, { backgroundColor: theme.cream }]}
                    onPress={onExploreCategories}
                    activeOpacity={0.85}
                  >
                    <Text style={[styles.ctaBtnText, { color: theme.creamInk, fontSize: fs(12) }]}>
                      Explore Categories
                    </Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          ) : null}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  header: {
    paddingHorizontal: 18,
    paddingTop: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
  },
  title: { fontWeight: '800' },
  summaryPill: {
    borderWidth: 1,
    borderRadius: 14,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  summaryPillText: { fontWeight: '700' },
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
  searchInput: { flex: 1, paddingVertical: 4 },
  searchBarBanner: {
    marginHorizontal: 18,
    marginTop: 10,
    marginBottom: 8,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 12,
    borderWidth: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 10,
  },
  searchBannerText: { fontWeight: '700', flex: 1 },
  searchBannerRight: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  viewTogglePill: {
    flexDirection: 'row',
    borderRadius: 10,
    borderWidth: 1,
    padding: 2,
    gap: 2,
  },
  viewToggleBtn: {
    borderRadius: 7,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  viewToggleText: { fontWeight: '600' },
  viewToggleTextActive: { fontWeight: '800' },
  backShelfBtn: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 9,
    paddingVertical: 4,
  },
  backShelfText: { fontWeight: '700' },
  listContent: { paddingHorizontal: 18, paddingTop: 4, paddingBottom: 112, gap: 10 },
  searchGridRow: {
    justifyContent: 'flex-start',
    gap: 10,
    marginBottom: 6,
  },
  searchGridTile: {
    width: '31%',
    alignItems: 'center',
    gap: 6,
  },
  searchGridTitle: {
    fontWeight: '700',
    lineHeight: 15.5,
    alignSelf: 'stretch',
  },
  searchGridAuthor: {
    alignSelf: 'stretch',
  },
  searchCard: {
    borderRadius: 16,
    padding: 11,
    flexDirection: 'row',
    gap: 12,
    borderWidth: 1,
  },
  shelfScroll: {
    paddingHorizontal: 18,
    paddingTop: 12,
    paddingBottom: 112,
    gap: 14,
  },
  heroCard: {
    borderRadius: 22,
    borderWidth: 1,
    padding: 14,
    gap: 11,
  },
  heroTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  heroBadge: {
    borderRadius: 9,
    paddingHorizontal: 9,
    paddingVertical: 4,
  },
  heroBadgeText: { fontWeight: '800', letterSpacing: 0.6 },
  heroBookmarkBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroBodyRow: {
    flexDirection: 'row',
    gap: 13,
    alignItems: 'center',
  },
  heroInfo: {
    flex: 1,
    gap: 5,
  },
  heroTitle: { fontWeight: '800', lineHeight: 20 },
  heroAuthor: {},
  heroProgWrap: { gap: 4, marginTop: 2 },
  heroProgMeta: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  heroProgLabel: { fontWeight: '800' },
  heroProgPages: {},
  progTrack: { height: 6, borderRadius: 3, overflow: 'hidden' },
  progFill: { height: '100%', borderRadius: 3 },
  continueBtn: {
    marginTop: 5,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderRadius: 13,
    paddingHorizontal: 14,
    paddingVertical: 8,
    alignSelf: 'flex-start',
  },
  continueBtnText: { fontWeight: '800' },
  segmentedBar: {
    flexDirection: 'row',
    borderRadius: 16,
    borderWidth: 1,
    padding: 4,
    gap: 4,
  },
  segItem: {
    flex: 1,
    borderRadius: 12,
    paddingVertical: 8,
    paddingHorizontal: 6,
    alignItems: 'center',
    justifyContent: 'center',
  },
  segText: { fontWeight: '600' },
  segTextActive: { fontWeight: '800' },
  sectionBlock: { gap: 10 },
  shelfRowCard: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 11,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  shelfRowBody: { flex: 1, gap: 3 },
  rowProgWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 4,
  },
  rowPctText: { fontWeight: '800', minWidth: 32, textAlign: 'right' },
  pillCta: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  pillCtaText: { fontWeight: '800' },
  heroHeaderBtns: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  readingRowActions: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  readingRemoveBtn: {
    width: 28,
    height: 28,
    borderRadius: 14,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  savedGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    rowGap: 11,
  },
  savedCard: {
    width: '48.2%',
    borderRadius: 18,
    borderWidth: 1,
    padding: 11,
    gap: 6,
  },
  savedCoverCenter: { alignItems: 'center', marginBottom: 2 },
  savedBookTitle: { fontWeight: '700', lineHeight: 17 },
  savedBookAuthor: {},
  savedActions: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 6,
    marginTop: 4,
  },
  savedReadBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  savedReadText: { fontWeight: '800' },
  savedRemovePill: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  savedRemoveText: { fontWeight: '600' },
  storageBanner: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 12,
    gap: 8,
  },
  storageTop: { gap: 3 },
  storageTitle: { fontWeight: '800' },
  storageMeta: { fontWeight: '600' },
  offlineBtnsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 5,
  },
  readOfflinePill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    borderRadius: 11,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  removeOfflineBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    borderWidth: 1,
    borderRadius: 11,
    paddingHorizontal: 9,
    paddingVertical: 5,
  },
  removeOfflineText: { fontWeight: '700' },
  cardBody: { flex: 1, justifyContent: 'space-between', gap: 3 },
  bookTitle: { fontWeight: '700', lineHeight: 19 },
  bookAuthor: {},
  bookMeta: { fontWeight: '600' },
  cardActions: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4 },
  readBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderRadius: 14,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  readBtnText: { fontWeight: '800' },
  actionCircle: {
    width: 31,
    height: 31,
    borderRadius: 16,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyShelfCard: {
    borderRadius: 18,
    borderWidth: 1,
    padding: 24,
    alignItems: 'center',
    gap: 8,
  },
  ctaBtn: {
    marginTop: 6,
    borderRadius: 14,
    paddingHorizontal: 16,
    paddingVertical: 9,
  },
  ctaBtnText: { fontWeight: '800' },
  emptyBox: { paddingVertical: 48, alignItems: 'center', gap: 6 },
  emptyTitle: { fontWeight: '700', textAlign: 'center' },
  emptySub: { textAlign: 'center', paddingHorizontal: 12, lineHeight: 17 },
});
