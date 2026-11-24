import React, { useMemo } from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { BookCover } from '../components/BookCover';
import { FlameIcon } from '../components/Icons';
import { useAppTheme } from '../context/ThemeContext';
import { formatBytes } from '../services/libraryStore';
import type { Book, BookProgress, OfflineBookEntry, ReadingStreak } from '../types';

interface Props {
  books: Book[];
  progressById: Record<string, BookProgress>;
  savedIds: string[];
  offlineById: Record<string, OfflineBookEntry>;
  streak: ReadingStreak;
  hideHeader?: boolean;
  onSelectCategory: (cat: string) => void;
  onOpenBookDetail: (book: Book) => void;
}

const WEEK_LETTERS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];

export function StatsScreen({
  books,
  progressById,
  savedIds,
  offlineById,
  streak,
  hideHeader = false,
  onSelectCategory,
  onOpenBookDetail,
}: Props) {
  const { theme, fs } = useAppTheme();

  const stats = useMemo(() => {
    const total = books.length;
    let totalBytes = 0;
    const byCat = new Map<string, number>();
    const byEdu = new Map<string, number>();
    const byFmt = new Map<string, number>();
    const bookById = new Map<string, Book>();

    for (const b of books) {
      bookById.set(b.id, b);
      totalBytes += b.size;
      byCat.set(b.cat, (byCat.get(b.cat) || 0) + 1);
      if (b.cat === 'Education & Textbooks') {
        const top = (b.sub || 'Other').split('/')[0];
        byEdu.set(top, (byEdu.get(top) || 0) + 1);
      }
      byFmt.set(b.fmt, (byFmt.get(b.fmt) || 0) + 1);
    }

    const offlineList = Object.values(offlineById);
    const offlineBytes = offlineList.reduce((acc, e) => acc + (e.size || 0), 0);

    const progressEntries = Object.values(progressById).sort((a, b) =>
      (b.updatedAt || '').localeCompare(a.updatedAt || '')
    );

    let completedCount = 0;
    let inProgressCount = 0;
    let totalPagesRead = 0;
    for (const p of progressEntries) {
      totalPagesRead += p.currentPage || 0;
      if (p.progressPct >= 100) completedCount++;
      else if (p.progressPct > 0 || p.currentPage > 0) inProgressCount++;
    }

    const recentProgressBooks = progressEntries
      .map((p) => {
        const book = bookById.get(p.bookId);
        return book ? { book, prog: p } : null;
      })
      .filter((x): x is { book: Book; prog: BookProgress } => Boolean(x))
      .slice(0, 6);

    return {
      total,
      totalBytes,
      offlineCount: offlineList.length,
      offlineBytes,
      completedCount,
      inProgressCount,
      totalPagesRead,
      recentProgressBooks,
      cats: [...byCat.entries()].sort((a, b) => b[1] - a[1]),
      edu: [...byEdu.entries()].sort((a, b) => b[1] - a[1]),
      fmts: [...byFmt.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6),
    };
  }, [books, offlineById, progressById]);

  const maxCat = stats.cats[0]?.[1] || 1;
  const maxEdu = stats.edu[0]?.[1] || 1;

  return (
    <ScrollView
      style={[styles.root, { backgroundColor: theme.bg }]}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      {/* Single Clean Header (No second subtitle) */}
      {!hideHeader ? (
        <Text style={[styles.heading, { color: theme.ink, fontSize: fs(24) }]}>STATS</Text>
      ) : null}

      {/* Reading Streak & Weekly Activity Card */}
      <View style={[styles.streakCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
        <View style={styles.streakTop}>
          <View>
            <Text style={[styles.streakLabel, { color: theme.muted, fontSize: fs(10) }]}>READING STREAK</Text>
            <View style={styles.streakValRow}>
              <FlameIcon size={22} color={theme.accent} />
              <Text style={[styles.streakVal, { color: theme.ink, fontSize: fs(22) }]}>
                {streak.days} {streak.days === 1 ? 'day' : 'days'}
              </Text>
            </View>
          </View>
          <View style={[styles.lastActivePill, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
            <Text style={[styles.lastActiveText, { color: theme.cream, fontSize: fs(11) }]}>
              {streak.lastReadDate || 'Today'}
            </Text>
          </View>
        </View>

        <View style={styles.weekRow}>
          {WEEK_LETTERS.map((letter, idx) => {
            const active = streak.weekDaysActive.includes(idx);
            return (
              <View key={`${letter}-${idx}`} style={styles.dayCol}>
                <View
                  style={[
                    styles.dayDot,
                    {
                      backgroundColor: active ? theme.accent : theme.surfaceAlt,
                      borderColor: active ? theme.accent : theme.border,
                    },
                  ]}
                >
                  <Text
                    style={[
                      styles.dayDotMark,
                      { color: active ? theme.creamInk : theme.muted },
                      active && styles.dayDotMarkActive,
                    ]}
                  >
                    {active ? '✓' : '·'}
                  </Text>
                </View>
                <Text
                  style={[
                    styles.dayLetter,
                    { color: active ? theme.ink : theme.muted },
                    active && styles.dayLetterActive,
                  ]}
                >
                  {letter}
                </Text>
              </View>
            );
          })}
        </View>
      </View>

      {/* Personal Reading 2x2 KPI Grid */}
      <View style={styles.kpiGrid}>
        <View style={[styles.kpiCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <Text style={[styles.kpiLabel, { color: theme.muted, fontSize: fs(10) }]}>COMPLETED</Text>
          <Text style={[styles.kpiVal, { color: theme.ink, fontSize: fs(22) }]}>{stats.completedCount}</Text>
          <Text style={[styles.kpiHint, { color: theme.accent, fontSize: fs(11) }]}>100% finished</Text>
        </View>
        <View style={[styles.kpiCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <Text style={[styles.kpiLabel, { color: theme.muted, fontSize: fs(10) }]}>IN PROGRESS</Text>
          <Text style={[styles.kpiVal, { color: theme.ink, fontSize: fs(22) }]}>{stats.inProgressCount}</Text>
          <Text style={[styles.kpiHint, { color: theme.accent, fontSize: fs(11) }]}>active reads</Text>
        </View>
        <View style={[styles.kpiCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <Text style={[styles.kpiLabel, { color: theme.muted, fontSize: fs(10) }]}>PAGES READ</Text>
          <Text style={[styles.kpiVal, { color: theme.ink, fontSize: fs(22) }]}>
            {stats.totalPagesRead.toLocaleString()}
          </Text>
          <Text style={[styles.kpiHint, { color: theme.accent, fontSize: fs(11) }]}>logged pages</Text>
        </View>
        <View style={[styles.kpiCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <Text style={[styles.kpiLabel, { color: theme.muted, fontSize: fs(10) }]}>OFFLINE</Text>
          <Text style={[styles.kpiVal, { color: theme.ink, fontSize: fs(22) }]}>{stats.offlineCount}</Text>
          <Text style={[styles.kpiHint, { color: theme.accent, fontSize: fs(11) }]}>
            {formatBytes(stats.offlineBytes)}
          </Text>
        </View>
      </View>

      {/* Compact Bookmarks + Catalog Summary Bar */}
      <View style={styles.summaryRow}>
        <View style={[styles.summaryPill, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
          <Text style={[styles.summaryLabel, { color: theme.muted }]}>Bookmarked</Text>
          <Text style={[styles.summaryVal, { color: theme.cream, fontSize: fs(13) }]}>{savedIds.length}</Text>
        </View>
        <View style={[styles.summaryPill, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
          <Text style={[styles.summaryLabel, { color: theme.muted }]}>Catalog</Text>
          <Text style={[styles.summaryVal, { color: theme.cream, fontSize: fs(13) }]}>
            {stats.total.toLocaleString()} ({formatBytes(stats.totalBytes)})
          </Text>
        </View>
      </View>

      {/* Personal Reading Progress List */}
      <View style={[styles.panel, { backgroundColor: theme.surface, borderColor: theme.border }]}>
        <Text style={[styles.panelTitle, { color: theme.ink, fontSize: fs(15) }]}>Reading Progress</Text>
        {stats.recentProgressBooks.length === 0 ? (
          <Text style={[styles.emptyProgressText, { color: theme.muted, fontSize: fs(12) }]}>
            No page progress logged yet.
          </Text>
        ) : (
          <View style={styles.progressList}>
            {stats.recentProgressBooks.map(({ book, prog }) => (
              <TouchableOpacity
                key={book.id}
                style={[styles.progressItem, { backgroundColor: theme.surfaceAlt, borderColor: theme.borderSubtle }]}
                onPress={() => onOpenBookDetail(book)}
                activeOpacity={0.8}
              >
                <BookCover
                  book={book}
                  localCoverUri={offlineById[book.id]?.coverLocalUri}
                  width={42}
                  height={60}
                  borderRadius={6}
                  isOffline={Boolean(offlineById[book.id])}
                />
                <View style={styles.progressInfo}>
                  <Text style={[styles.progressTitle, { color: theme.ink, fontSize: fs(13) }]} numberOfLines={1}>
                    {book.title}
                  </Text>
                  <Text style={[styles.progressMeta, { color: theme.accent, fontSize: fs(11) }]}>
                    p.{prog.currentPage}/{prog.totalPages || '?'} · {prog.progressPct}%
                  </Text>
                  <View style={[styles.track, { backgroundColor: theme.surface }]}>
                    <View
                      style={[
                        styles.fill,
                        {
                          width: `${Math.max(4, Math.min(100, prog.progressPct))}%`,
                          backgroundColor: prog.progressPct >= 100 ? theme.sage : theme.accent,
                        },
                      ]}
                    />
                  </View>
                </View>
              </TouchableOpacity>
            ))}
          </View>
        )}
      </View>

      {/* Library Categories (Tap to Explore) */}
      <View style={[styles.panel, { backgroundColor: theme.surface, borderColor: theme.border }]}>
        <Text style={[styles.panelTitle, { color: theme.ink, fontSize: fs(15) }]}>Categories</Text>
        {stats.cats.map(([cat, cnt]) => (
          <TouchableOpacity
            key={cat}
            style={styles.barRow}
            onPress={() => onSelectCategory(cat)}
            activeOpacity={0.75}
          >
            <View style={styles.barTop}>
              <Text style={[styles.barLabel, { color: theme.cream, fontSize: fs(12) }]} numberOfLines={1}>
                {cat}
              </Text>
              <Text style={[styles.barCount, { color: theme.muted, fontSize: fs(12) }]}>{cnt.toLocaleString()}</Text>
            </View>
            <View style={[styles.track, { backgroundColor: theme.surfaceAlt }]}>
              <View
                style={[styles.fill, { backgroundColor: theme.accent, width: `${Math.max(4, (cnt / maxCat) * 100)}%` }]}
              />
            </View>
          </TouchableOpacity>
        ))}
      </View>

      <View style={[styles.panel, { backgroundColor: theme.surface, borderColor: theme.border }]}>
        <Text style={[styles.panelTitle, { color: theme.ink, fontSize: fs(15) }]}>Education Breakdown</Text>
        {stats.edu.map(([name, cnt]) => (
          <View key={name} style={styles.barRow}>
            <View style={styles.barTop}>
              <Text style={[styles.barLabel, { color: theme.cream, fontSize: fs(12) }]}>{name}</Text>
              <Text style={[styles.barCount, { color: theme.muted, fontSize: fs(12) }]}>{cnt.toLocaleString()}</Text>
            </View>
            <View style={[styles.track, { backgroundColor: theme.surfaceAlt }]}>
              <View
                style={[
                  styles.fill,
                  { backgroundColor: theme.sage, width: `${Math.max(4, (cnt / maxEdu) * 100)}%` },
                ]}
              />
            </View>
          </View>
        ))}
      </View>

      <View style={[styles.panel, { backgroundColor: theme.surface, borderColor: theme.border }]}>
        <Text style={[styles.panelTitle, { color: theme.ink, fontSize: fs(15) }]}>Formats</Text>
        <View style={styles.fmtGrid}>
          {stats.fmts.map(([fmt, cnt]) => (
            <View
              key={fmt}
              style={[styles.fmtPill, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
            >
              <Text style={[styles.fmtName, { color: theme.ink, fontSize: fs(12) }]}>{fmt}</Text>
              <Text style={[styles.fmtCnt, { color: theme.muted, fontSize: fs(11) }]}>{cnt.toLocaleString()}</Text>
            </View>
          ))}
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  content: { paddingHorizontal: 18, paddingTop: 12, paddingBottom: 112, gap: 16 },
  heading: { fontWeight: '800' },
  streakCard: {
    borderRadius: 20,
    padding: 16,
    borderWidth: 1,
    gap: 14,
  },
  streakTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
  },
  streakLabel: { fontWeight: '700', letterSpacing: 0.7 },
  streakValRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 3 },
  streakVal: { fontWeight: '800' },
  lastActivePill: {
    borderRadius: 12,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  lastActiveText: { fontWeight: '600' },
  weekRow: { flexDirection: 'row', justifyContent: 'space-between', paddingHorizontal: 4 },
  dayCol: { alignItems: 'center', gap: 5 },
  dayDot: {
    width: 32,
    height: 32,
    borderRadius: 16,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dayDotMark: { fontSize: 13, fontWeight: '700' },
  dayDotMarkActive: { fontWeight: '800' },
  dayLetter: { fontSize: 11, fontWeight: '600' },
  dayLetterActive: { fontWeight: '800' },
  kpiGrid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: 10 },
  kpiCard: {
    width: '48.2%',
    borderRadius: 18,
    padding: 14,
    borderWidth: 1,
    gap: 3,
  },
  kpiLabel: { fontWeight: '700', letterSpacing: 0.7 },
  kpiVal: { fontWeight: '800' },
  kpiHint: {},
  summaryRow: { flexDirection: 'row', gap: 10 },
  summaryPill: {
    flex: 1,
    borderRadius: 14,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 10,
    gap: 2,
  },
  summaryLabel: { fontSize: 10, fontWeight: '700', textTransform: 'uppercase' },
  summaryVal: { fontWeight: '800' },
  panel: {
    borderRadius: 20,
    padding: 16,
    borderWidth: 1,
    gap: 10,
  },
  panelTitle: { fontWeight: '700', marginBottom: 2 },
  emptyProgressText: { lineHeight: 18 },
  progressList: { gap: 10 },
  progressItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    borderRadius: 12,
    padding: 9,
    borderWidth: 1,
  },
  progressInfo: { flex: 1, gap: 5 },
  progressTitle: { fontWeight: '700' },
  progressMeta: { fontWeight: '600' },
  barRow: { gap: 4 },
  barTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  barLabel: { fontWeight: '600', flex: 1, marginRight: 8 },
  barCount: { fontWeight: '700' },
  track: { height: 8, borderRadius: 4, overflow: 'hidden' },
  fill: { height: '100%', borderRadius: 4 },
  fmtGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  fmtPill: {
    borderRadius: 12,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 8,
    minWidth: '30%',
  },
  fmtName: { fontWeight: '800' },
  fmtCnt: {},
});
