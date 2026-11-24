import React, { useMemo, useState } from 'react';
import { Image, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { AuthorAvatar } from '../components/AuthorAvatar';
import { BookCover } from '../components/BookCover';
import {
  BookOpenIcon,
  ChevronRightIcon,
  CloseIcon,
  DownloadIcon,
  FlameIcon,
  OfflineIcon,
  SparklesIcon,
} from '../components/Icons';
import { useAppTheme } from '../context/ThemeContext';
import { formatBytes } from '../services/libraryStore';
import { QUOTES } from '../theme';
import type { Book, BookProgress, OfflineBookEntry, ReadingStreak } from '../types';

interface Props {
  books: Book[];
  currentlyReading: Book | null;
  progressById: Record<string, BookProgress>;
  offlineById: Record<string, OfflineBookEntry>;
  savedIds: string[];
  streak: ReadingStreak;
  downloadingMap: Record<string, number>;
  onContinueReading: (book: Book) => void;
  onOpenBookDetail: (book: Book) => void;
  onMakeOffline: (book: Book) => void;
  onExplorePath: (path: string[]) => void;
  onBrowseLibrary: () => void;
  onRemoveFromReading: (bookId: string) => void;
}

const WEEK_LETTERS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];

export function HomeScreen({
  books,
  currentlyReading,
  progressById,
  offlineById,
  savedIds,
  streak,
  downloadingMap,
  onContinueReading,
  onOpenBookDetail,
  onMakeOffline,
  onExplorePath,
  onBrowseLibrary,
  onRemoveFromReading,
}: Props) {
  const { theme, fs } = useAppTheme();
  const [quoteIdx, setQuoteIdx] = useState(0);

  const dateLabel = useMemo(() => {
    try {
      return new Date().toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return 'Today';
    }
  }, []);

  const offlineCount = Object.keys(offlineById).length;
  const featuredBook = currentlyReading;

  const featuredProg = featuredBook ? progressById[featuredBook.id] : undefined;
  const featuredOffline = featuredBook ? offlineById[featuredBook.id] : undefined;
  const featuredDlPct = featuredBook ? downloadingMap[featuredBook.id] : undefined;
  const featuredPct = featuredProg?.progressPct ?? (featuredOffline ? 100 : 0);

  // Personalized "Suggested For You" recommendations from reading history & bookmarks
  const suggestedBooks = useMemo(() => {
    if (!books.length) return [] as { book: Book; reason: string }[];
    const byId = new Map(books.map((b) => [b.id, b]));
    const seedIds = new Set<string>([
      ...(featuredBook ? [featuredBook.id] : []),
      ...savedIds,
      ...Object.keys(offlineById),
      ...Object.keys(progressById),
    ]);

    const prefAuthors = new Map<string, number>();
    const prefSubs = new Map<string, number>();
    const prefCats = new Map<string, number>();

    for (const id of seedIds) {
      const sb = byId.get(id);
      if (!sb) continue;
      if (sb.author && sb.author !== 'Unknown') {
        prefAuthors.set(sb.author, (prefAuthors.get(sb.author) || 0) + 4);
      }
      if (sb.sub) {
        prefSubs.set(sb.sub, (prefSubs.get(sb.sub) || 0) + 3);
      }
      prefCats.set(sb.cat, (prefCats.get(sb.cat) || 0) + 1);
    }

    const candidates: { book: Book; score: number; reason: string }[] = [];
    const seenCatMix = new Map<string, number>();

    for (const b of books) {
      if (featuredBook && b.id === featuredBook.id) continue;
      if (progressById[b.id] && progressById[b.id].progressPct >= 100) continue;

      let score = b.coverId ? 3 : 0;
      let reason = (b.sub || b.cat).split('/').pop() || b.cat;

      if (prefAuthors.has(b.author)) {
        score += (prefAuthors.get(b.author) || 0) * 3;
        reason = b.author;
      } else if (b.sub && prefSubs.has(b.sub)) {
        score += (prefSubs.get(b.sub) || 0) * 2;
      } else if (prefCats.has(b.cat)) {
        score += prefCats.get(b.cat) || 0;
      }

      if (score > 2) {
        candidates.push({ book: b, score, reason });
      }
      if (candidates.length >= 250) break;
    }

    candidates.sort((a, b) => b.score - a.score);
    const out: { book: Book; reason: string }[] = [];
    const used = new Set<string>();

    for (const c of candidates) {
      const catCnt = seenCatMix.get(c.book.cat) || 0;
      if (out.length < 10 && !used.has(c.book.id) && (prefAuthors.size > 0 || catCnt < 3)) {
        used.add(c.book.id);
        seenCatMix.set(c.book.cat, catCnt + 1);
        out.push({ book: c.book, reason: c.reason });
      }
      if (out.length >= 10) break;
    }

    if (out.length < 10) {
      for (const b of books) {
        if (!used.has(b.id) && b.coverId && (!featuredBook || b.id !== featuredBook.id)) {
          used.add(b.id);
          out.push({ book: b, reason: (b.sub || b.cat).split('/').pop() || b.cat });
        }
        if (out.length >= 10) break;
      }
    }
    return out;
  }, [books, featuredBook, savedIds, offlineById, progressById]);

  const shelfBooks = useMemo(() => {
    const picked: Book[] = [];
    const seen = new Set<string>(featuredBook ? [featuredBook.id] : []);
    const byId = new Map(books.map((b) => [b.id, b]));
    for (const id of [...Object.keys(offlineById), ...savedIds, ...Object.keys(progressById)]) {
      const b = byId.get(id);
      if (b && !seen.has(b.id)) {
        seen.add(b.id);
        picked.push(b);
      }
      if (picked.length >= 12) break;
    }
    if (picked.length < 12) {
      for (const b of books) {
        if (!seen.has(b.id) && b.coverId) {
          seen.add(b.id);
          picked.push(b);
        }
        if (picked.length >= 12) break;
      }
    }
    return picked;
  }, [books, featuredBook, offlineById, savedIds, progressById]);

  const popularAuthors = useMemo(() => {
    const map = new Map<string, { name: string; group: string; count: number }>();
    for (const b of books) {
      if (b.cat !== 'Authors & Scholars' || !b.sub) continue;
      const parts = b.sub.split('/').filter(Boolean);
      if (parts.length < 2) continue;
      const group = parts[0];
      const name = parts[1];
      const key = `${group}/${name}`;
      const existing = map.get(key);
      if (existing) existing.count++;
      else map.set(key, { name, group, count: 1 });
    }
    return [...map.values()].sort((a, b) => b.count - a.count).slice(0, 14);
  }, [books]);

  const quote = QUOTES[quoteIdx % QUOTES.length];

  return (
    <ScrollView
      style={[styles.root, { backgroundColor: theme.bg }]}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      {/* Single Clean Masthead Row */}
      <View style={styles.headerRow}>
        <View style={styles.brandRow}>
          <Image source={require('../../assets/icon.png')} style={styles.brandLogo} />
          <Text style={[styles.heading, { color: theme.ink, fontSize: fs(21) }]} numberOfLines={1}>
            ANABOOK
          </Text>
        </View>
        <View style={[styles.datePill, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <Text style={[styles.dateText, { color: theme.accent, fontSize: fs(11) }]}>{dateLabel}</Text>
        </View>
      </View>

      {/* Featured / Continue Reading Card */}
      {featuredBook ? (
        <View style={styles.sectionBlock}>
          <View style={styles.sectionHead}>
            <Text style={[styles.sectionTitle, { color: theme.ink, fontSize: fs(17) }]}>Continue reading</Text>
            <TouchableOpacity style={styles.moreLinkBtn} onPress={onBrowseLibrary}>
              <Text style={[styles.sectionAction, { color: theme.accent, fontSize: fs(12) }]}>All</Text>
              <ChevronRightIcon size={15} color={theme.accent} />
            </TouchableOpacity>
          </View>

          <View style={[styles.heroCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
            <TouchableOpacity
              onPress={() => onOpenBookDetail(featuredBook)}
              activeOpacity={0.88}
            >
              <BookCover
                book={featuredBook}
                localCoverUri={featuredOffline?.coverLocalUri}
                width={102}
                height={150}
                borderRadius={10}
                isOffline={Boolean(featuredOffline)}
              />
            </TouchableOpacity>

            <View style={styles.heroDetails}>
              <View style={styles.heroTopMetaRow}>
                <View style={[styles.heroCatPill, { backgroundColor: theme.accentSoft }]}>
                  <Text style={[styles.heroCategory, { color: theme.accent, fontSize: fs(10) }]} numberOfLines={1}>
                    {(featuredBook.sub || featuredBook.cat).split('/').pop()}
                  </Text>
                </View>

                <TouchableOpacity
                  style={[styles.heroDismissBtn, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
                  onPress={() => onRemoveFromReading(featuredBook.id)}
                  accessibilityLabel="Remove from Continue Reading"
                >
                  <CloseIcon size={13} color={theme.muted} />
                </TouchableOpacity>
              </View>

              <TouchableOpacity onPress={() => onOpenBookDetail(featuredBook)} activeOpacity={0.85}>
                <Text style={[styles.heroTitle, { color: theme.ink, fontSize: fs(17) }]} numberOfLines={2}>
                  {featuredBook.title}
                </Text>
              </TouchableOpacity>

              <Text style={[styles.heroAuthor, { color: theme.muted, fontSize: fs(11.5) }]} numberOfLines={1}>
                {featuredBook.author} · {featuredBook.fmt}
              </Text>

              <View style={styles.heroProgWrap}>
                <View style={[styles.heroProgTrack, { backgroundColor: theme.surfaceAlt }]}>
                  <View
                    style={[
                      styles.heroProgFill,
                      { width: `${Math.max(featuredPct > 0 ? 5 : 2, Math.min(100, Math.round(featuredPct)))}%`, backgroundColor: theme.accent },
                    ]}
                  />
                </View>
                <Text style={[styles.heroProgPct, { color: theme.accent, fontSize: fs(11) }]}>
                  {Math.round(featuredPct)}%
                </Text>
              </View>

              <View style={styles.heroBtnRow}>
                <TouchableOpacity
                  style={[styles.continueBtn, { backgroundColor: theme.cream }]}
                  onPress={() => onContinueReading(featuredBook)}
                  activeOpacity={0.88}
                >
                  <BookOpenIcon size={15} color={theme.creamInk} />
                  <Text style={[styles.continueBtnText, { color: theme.creamInk, fontSize: fs(12) }]}>
                    {featuredOffline ? 'Read Offline' : 'Continue'}
                  </Text>
                </TouchableOpacity>

                {featuredOffline ? (
                  <View
                    style={[styles.heroIconBtn, { backgroundColor: theme.sage, borderColor: theme.sage }]}
                    accessibilityLabel="Available offline"
                  >
                    <OfflineIcon size={16} color={theme.ink} />
                  </View>
                ) : featuredDlPct !== undefined ? (
                  <View style={[styles.heroIconBtn, { borderColor: theme.accent }]}>
                    <Text style={[styles.dlPctSmall, { color: theme.accent }]}>{featuredDlPct}%</Text>
                  </View>
                ) : (
                  <TouchableOpacity
                    style={[styles.heroIconBtn, { borderColor: theme.accent }]}
                    onPress={() => onMakeOffline(featuredBook)}
                    accessibilityLabel="Download offline"
                  >
                    <DownloadIcon size={16} color={theme.accent} />
                  </TouchableOpacity>
                )}
              </View>
            </View>
          </View>
        </View>
      ) : null}

      {/* Personalized "Suggested For You" Section */}
      {suggestedBooks.length > 0 ? (
        <View style={styles.sectionBlock}>
          <View style={styles.sectionHead}>
            <View style={styles.titleWithIcon}>
              <SparklesIcon size={16} color={theme.accent} />
              <Text style={[styles.sectionTitle, { color: theme.ink, fontSize: fs(17) }]}>Suggested For You</Text>
            </View>
            <TouchableOpacity style={styles.moreLinkBtn} onPress={() => onExplorePath([])}>
              <Text style={[styles.sectionAction, { color: theme.accent, fontSize: fs(12) }]}>Explore</Text>
              <ChevronRightIcon size={15} color={theme.accent} />
            </TouchableOpacity>
          </View>

          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.recScroll}
          >
            {suggestedBooks.map(({ book, reason }) => {
              const offline = offlineById[book.id];
              return (
                <TouchableOpacity
                  key={book.id}
                  style={[styles.recCard, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
                  onPress={() => onOpenBookDetail(book)}
                  activeOpacity={0.85}
                >
                  <BookCover
                    book={book}
                    localCoverUri={offline?.coverLocalUri}
                    width={106}
                    height={154}
                    borderRadius={10}
                    isOffline={Boolean(offline)}
                  />
                  <View style={[styles.reasonPill, { backgroundColor: theme.accentSoft }]}>
                    <Text style={[styles.reasonText, { color: theme.accent, fontSize: fs(10) }]} numberOfLines={1}>
                      {reason}
                    </Text>
                  </View>
                  <Text style={[styles.recTitle, { color: theme.ink, fontSize: fs(12) }]} numberOfLines={2}>
                    {book.title}
                  </Text>
                  <Text style={[styles.recAuthor, { color: theme.muted, fontSize: fs(10.5) }]} numberOfLines={1}>
                    {book.author}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>
        </View>
      ) : null}

      {/* Popular Authors Portrait Strip */}
      {popularAuthors.length > 0 ? (
        <View style={styles.sectionBlock}>
          <View style={styles.sectionHead}>
            <Text style={[styles.sectionTitle, { color: theme.ink, fontSize: fs(17) }]}>Popular Authors</Text>
            <TouchableOpacity style={styles.moreLinkBtn} onPress={() => onExplorePath(['Authors & Scholars'])}>
              <Text style={[styles.sectionAction, { color: theme.accent, fontSize: fs(12) }]}>All</Text>
              <ChevronRightIcon size={15} color={theme.accent} />
            </TouchableOpacity>
          </View>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.authorsScroll}
          >
            {popularAuthors.map((au) => (
              <TouchableOpacity
                key={`${au.group}-${au.name}`}
                style={styles.authorItem}
                onPress={() => onExplorePath(['Authors & Scholars', au.group, au.name])}
                activeOpacity={0.82}
              >
                <AuthorAvatar name={au.name} size={56} />
                <Text style={[styles.authorChipName, { color: theme.ink, fontSize: fs(11) }]} numberOfLines={2}>
                  {au.name}
                </Text>
                <Text style={[styles.authorChipCount, { color: theme.accent, fontSize: fs(10) }]}>
                  {au.count} books
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>
      ) : null}

      {/* Discover & Offline 3-Column Visual Bookshelf Grid */}
      <View style={styles.sectionBlock}>
        <View style={styles.sectionHead}>
          <Text style={[styles.sectionTitle, { color: theme.ink, fontSize: fs(17) }]}>
            {offlineCount > 0 ? 'Offline & Recent' : 'Discover'}
          </Text>
          <TouchableOpacity style={styles.moreLinkBtn} onPress={onBrowseLibrary}>
            <Text style={[styles.sectionAction, { color: theme.accent, fontSize: fs(12) }]}>Shelf</Text>
            <ChevronRightIcon size={15} color={theme.accent} />
          </TouchableOpacity>
        </View>
        <View style={styles.discoverGrid}>
          {shelfBooks.slice(0, 9).map((item) => {
            const offline = offlineById[item.id];
            return (
              <TouchableOpacity
                key={item.id}
                style={styles.discoverTile}
                onPress={() => onOpenBookDetail(item)}
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
                <Text style={[styles.discoverTitle, { color: theme.ink, fontSize: fs(11.5) }]} numberOfLines={2}>
                  {item.title}
                </Text>
                <Text style={[styles.discoverAuthor, { color: theme.muted, fontSize: fs(10) }]} numberOfLines={1}>
                  {item.author}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>

      {/* Compact Streak + Quote Companion Card */}
      <View style={[styles.companionCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
        <View style={styles.streakRow}>
          <View style={styles.streakLeft}>
            <View style={styles.streakInline}>
              <FlameIcon size={20} color={theme.accent} />
              <Text style={[styles.streakNum, { color: theme.ink, fontSize: fs(21) }]}>{streak.days}</Text>
            </View>
            <Text style={[styles.streakLabel, { color: theme.cream, fontSize: fs(11) }]}>day streak</Text>
          </View>
          <View style={styles.weekDots}>
            {WEEK_LETTERS.map((l, i) => {
              const active = streak.weekDaysActive.includes(i);
              return (
                <View key={`${l}-${i}`} style={styles.dayCol}>
                  <Text style={[styles.weekLetter, { color: theme.muted }]}>{l}</Text>
                  <View
                    style={[
                      styles.dayCircle,
                      active
                        ? { backgroundColor: theme.sage }
                        : { borderWidth: 1.2, borderStyle: 'dashed', borderColor: theme.muted },
                    ]}
                  >
                    {active ? <View style={[styles.dayInnerDot, { backgroundColor: theme.creamInk }]} /> : null}
                  </View>
                </View>
              );
            })}
          </View>
        </View>

        <View style={[styles.quoteDivider, { backgroundColor: theme.border }]} />

        <Text style={[styles.quoteBody, { color: theme.cream, fontSize: fs(13) }]}>“{quote.text}”</Text>
        <View style={styles.quoteFooter}>
          <Text style={[styles.quoteAuthor, { color: theme.muted, fontSize: fs(11) }]} numberOfLines={1}>
            — {quote.author}
          </Text>
          <TouchableOpacity onPress={() => setQuoteIdx((n) => n + 1)}>
            <ChevronRightIcon size={16} color={theme.accent} />
          </TouchableOpacity>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  content: { paddingHorizontal: 18, paddingTop: 12, paddingBottom: 112, gap: 20 },
  headerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 },
  brandRow: { flexDirection: 'row', alignItems: 'center', gap: 10, flex: 1 },
  brandLogo: { width: 32, height: 32, borderRadius: 9 },
  heading: { fontWeight: '800', letterSpacing: 0.3 },
  datePill: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  dateText: { fontWeight: '700' },
  sectionBlock: { gap: 10 },
  sectionHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  titleWithIcon: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  sectionTitle: { fontWeight: '700' },
  moreLinkBtn: { flexDirection: 'row', alignItems: 'center', gap: 2 },
  sectionAction: { fontWeight: '700' },
  heroCard: {
    borderRadius: 22,
    padding: 15,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    gap: 14,
  },
  heroDetails: { flex: 1, gap: 5 },
  heroTopMetaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  heroCatPill: {
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 3,
    flexShrink: 1,
  },
  heroDismissBtn: {
    width: 26,
    height: 26,
    borderRadius: 13,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroCategory: { fontWeight: '800', textTransform: 'uppercase', letterSpacing: 0.6 },
  heroTitle: { fontWeight: '800', lineHeight: 22 },
  heroAuthor: {},
  heroProgWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 3,
  },
  heroProgTrack: { flex: 1, height: 6, borderRadius: 3, overflow: 'hidden' },
  heroProgFill: { height: '100%', borderRadius: 3 },
  heroProgPct: { fontWeight: '800', minWidth: 30, textAlign: 'right' },
  heroBtnRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 6 },
  continueBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 9,
  },
  continueBtnText: { fontWeight: '800' },
  heroIconBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dlPctSmall: { fontSize: 10, fontWeight: '800' },
  recScroll: { gap: 12, paddingRight: 8 },
  recCard: {
    width: 126,
    borderRadius: 16,
    borderWidth: 1,
    padding: 9,
    gap: 6,
  },
  reasonPill: {
    borderRadius: 8,
    paddingHorizontal: 7,
    paddingVertical: 2,
    alignSelf: 'flex-start',
    maxWidth: '100%',
  },
  reasonText: { fontWeight: '700' },
  recTitle: { fontWeight: '700', lineHeight: 16 },
  recAuthor: {},
  authorsScroll: { gap: 12, paddingRight: 8 },
  authorItem: { width: 82, alignItems: 'center', gap: 5 },
  authorChipName: { fontWeight: '700', textAlign: 'center', lineHeight: 14 },
  authorChipCount: { fontWeight: '600' },
  discoverGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'flex-start',
    gap: 10,
    rowGap: 16,
  },
  discoverTile: {
    width: '31%',
    alignItems: 'center',
    gap: 6,
  },
  discoverTitle: {
    fontWeight: '700',
    lineHeight: 15.5,
    alignSelf: 'stretch',
  },
  discoverAuthor: {
    alignSelf: 'stretch',
  },
  companionCard: {
    borderRadius: 20,
    padding: 16,
    borderWidth: 1,
    gap: 10,
  },
  streakRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 },
  streakLeft: { gap: 2 },
  streakInline: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  streakNum: { fontWeight: '800' },
  streakLabel: { fontWeight: '500' },
  weekDots: { flexDirection: 'row', gap: 6 },
  dayCol: { alignItems: 'center', gap: 4 },
  weekLetter: { fontSize: 10, fontWeight: '600' },
  dayCircle: { width: 18, height: 18, borderRadius: 9, alignItems: 'center', justifyContent: 'center' },
  dayInnerDot: { width: 4, height: 4, borderRadius: 2 },
  quoteDivider: { height: StyleSheet.hairlineWidth },
  quoteBody: { lineHeight: 19 },
  quoteFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  quoteAuthor: { flex: 1, marginRight: 8 },
});
