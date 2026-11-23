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
  CheckCircleIcon,
  CloseIcon,
  DownloadIcon,
  SearchIcon,
} from '../components/Icons';
import { useAppTheme } from '../context/ThemeContext';
import { formatBytes } from '../services/libraryStore';
import type { Book, OfflineBookEntry } from '../types';

interface Props {
  books: Book[];
  categories: string[];
  offlineById: Record<string, OfflineBookEntry>;
  downloadingMap: Record<string, number>;
  initialCategory?: string;
  initialSubcategory?: string;
  onClearSubcategory?: () => void;
  onOpenDetail: (book: Book) => void;
  onQuickRead: (book: Book) => void;
  onMakeOffline: (book: Book) => void;
}

export function LibraryScreen({
  books,
  categories,
  offlineById,
  downloadingMap,
  initialCategory = '',
  initialSubcategory = '',
  onClearSubcategory,
  onOpenDetail,
  onQuickRead,
  onMakeOffline,
}: Props) {
  const { theme, fs } = useAppTheme();
  const [query, setQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState<string>(initialCategory || 'ALL');
  const [subFilter, setSubFilter] = useState<string>(initialSubcategory || '');

  useEffect(() => {
    if (initialCategory) {
      setSelectedFilter(initialCategory);
    }
    setSubFilter(initialSubcategory || '');
  }, [initialCategory, initialSubcategory]);

  const filterChips = useMemo(() => {
    const offlineCount = Object.keys(offlineById).length;
    return [
      { key: 'ALL', label: `All (${books.length.toLocaleString()})` },
      { key: 'OFFLINE', label: `Offline (${offlineCount})` },
      ...categories.map((c) => ({ key: c, label: c })),
    ];
  }, [books.length, categories, offlineById]);

  const filtered = useMemo(() => {
    const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    return books.filter((b) => {
      if (selectedFilter === 'OFFLINE' && !offlineById[b.id]) return false;
      if (selectedFilter !== 'ALL' && selectedFilter !== 'OFFLINE' && b.cat !== selectedFilter) {
        return false;
      }
      if (subFilter) {
        if (b.sub !== subFilter && !b.sub.startsWith(subFilter + '/')) return false;
      }
      if (terms.length > 0) {
        for (const t of terms) {
          if (!b.searchBlob.includes(t)) return false;
        }
      }
      return true;
    });
  }, [books, query, selectedFilter, subFilter, offlineById]);

  return (
    <View style={[styles.root, { backgroundColor: theme.bg }]}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.ink, fontSize: fs(24) }]}>LIBRARY</Text>
        <View style={[styles.countPill, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <Text style={[styles.countText, { color: theme.accent, fontSize: fs(11.5) }]}>
            {filtered.length.toLocaleString()}
          </Text>
        </View>
      </View>

      <View style={styles.searchWrap}>
        <View style={[styles.searchBox, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
          <SearchIcon size={17} color={theme.muted} />
          <TextInput
            style={[styles.searchInput, { color: theme.ink, fontSize: fs(13.5) }]}
            placeholder="Search title, author, subject…"
            placeholderTextColor={theme.muted}
            value={query}
            onChangeText={setQuery}
          />
          {query.length > 0 ? (
            <TouchableOpacity onPress={() => setQuery('')}>
              <CloseIcon size={16} color={theme.muted} />
            </TouchableOpacity>
          ) : null}
        </View>
      </View>

      <View style={styles.chipsOuter}>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.chipsScroll}
        >
          {filterChips.map((ch) => {
            const active = selectedFilter === ch.key;
            return (
              <TouchableOpacity
                key={ch.key}
                style={[
                  styles.chip,
                  {
                    backgroundColor: active ? theme.cream : theme.surfaceAlt,
                    borderColor: active ? theme.cream : theme.border,
                  },
                ]}
                onPress={() => {
                  setSelectedFilter(ch.key);
                  setSubFilter('');
                  onClearSubcategory?.();
                }}
                activeOpacity={0.8}
              >
                <Text
                  style={[
                    styles.chipText,
                    { color: active ? theme.creamInk : theme.cream, fontSize: fs(12) },
                    active && styles.chipTextActive,
                  ]}
                >
                  {ch.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>

      {subFilter ? (
        <View style={[styles.subBanner, { backgroundColor: theme.accentSoft, borderColor: theme.accent }]}>
          <Text style={[styles.subBannerText, { color: theme.cream, fontSize: fs(12) }]} numberOfLines={1}>
            {subFilter}
          </Text>
          <TouchableOpacity
            onPress={() => {
              setSubFilter('');
              onClearSubcategory?.();
            }}
          >
            <CloseIcon size={15} color={theme.accent} />
          </TouchableOpacity>
        </View>
      ) : null}

      <FlatList
        data={filtered}
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
              {selectedFilter === 'OFFLINE'
                ? 'Tap download on any book to save it offline.'
                : 'Try another search term or filter.'}
            </Text>
          </View>
        }
        renderItem={({ item }) => {
          const offline = offlineById[item.id];
          const dlPct = downloadingMap[item.id];
          const leafSub = (item.sub || item.cat).split('/').pop() || item.cat;

          return (
            <TouchableOpacity
              style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}
              onPress={() => onOpenDetail(item)}
              activeOpacity={0.85}
            >
              <BookCover
                book={item}
                localCoverUri={offline?.coverLocalUri}
                width={64}
                height={94}
                borderRadius={8}
                isOffline={Boolean(offline)}
              />

              <View style={styles.cardBody}>
                <Text style={[styles.bookTitle, { color: theme.ink, fontSize: fs(14) }]} numberOfLines={2}>
                  {item.title}
                </Text>
                <Text style={[styles.bookAuthor, { color: theme.muted, fontSize: fs(12) }]} numberOfLines={1}>
                  {item.author}
                </Text>
                <Text style={[styles.bookMeta, { color: theme.accent, fontSize: fs(11) }]} numberOfLines={1}>
                  {leafSub} · {item.fmt} · {formatBytes(item.size)}
                </Text>

                <View style={styles.cardActions}>
                  <TouchableOpacity
                    style={[styles.readBtn, { backgroundColor: theme.cream }]}
                    onPress={() => onQuickRead(item)}
                    activeOpacity={0.85}
                  >
                    <BookOpenIcon size={15} color={theme.creamInk} />
                    <Text style={[styles.readBtnText, { color: theme.creamInk, fontSize: fs(11.5) }]}>
                      {offline ? 'Offline' : 'Read'}
                    </Text>
                  </TouchableOpacity>

                  {offline ? (
                    <View style={[styles.actionCircle, { backgroundColor: theme.sage, borderColor: theme.sage }]}>
                      <CheckCircleIcon size={16} color={theme.ink} />
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
                      <DownloadIcon size={16} color={theme.accent} />
                    </TouchableOpacity>
                  )}
                </View>
              </View>
            </TouchableOpacity>
          );
        }}
      />
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
  },
  title: { fontWeight: '800' },
  countPill: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  countText: { fontWeight: '800' },
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
  chipsOuter: { marginTop: 10, marginBottom: 8 },
  chipsScroll: { paddingHorizontal: 18, gap: 8 },
  chip: {
    paddingHorizontal: 13,
    paddingVertical: 7,
    borderRadius: 18,
    borderWidth: 1,
  },
  chipText: { fontWeight: '600' },
  chipTextActive: { fontWeight: '800' },
  subBanner: {
    marginHorizontal: 18,
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
  subBannerText: { fontWeight: '700', flex: 1 },
  listContent: { paddingHorizontal: 18, paddingTop: 4, paddingBottom: 112, gap: 10 },
  card: {
    borderRadius: 16,
    padding: 11,
    flexDirection: 'row',
    gap: 12,
    borderWidth: 1,
  },
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
  emptyBox: { paddingVertical: 48, alignItems: 'center', gap: 6 },
  emptyTitle: { fontWeight: '700' },
  emptySub: { textAlign: 'center', paddingHorizontal: 20 },
});
