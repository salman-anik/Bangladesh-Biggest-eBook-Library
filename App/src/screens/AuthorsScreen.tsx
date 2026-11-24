import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  FlatList,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import { AuthorAvatar } from '../components/AuthorAvatar';
import { CloseIcon, SearchIcon } from '../components/Icons';
import { useAppTheme } from '../context/ThemeContext';
import type { Book, OfflineBookEntry } from '../types';

const PAGE_SIZE = 24;

type AuthorGroup = 'Bangladeshi Authors' | 'International Authors' | 'Islamic Scholars';
type GroupFilter = 'all' | AuthorGroup;

interface AuthorItem {
  key: string;
  name: string;
  group: AuthorGroup;
  path: string[];
  count: number;
  offlineCount: number;
  subfolderCount: number;
}

interface MutableAuthorAcc {
  key: string;
  name: string;
  group: AuthorGroup;
  path: string[];
  count: number;
  offlineCount: number;
  subfolders: Set<string>;
}

const GROUP_FILTERS: { key: GroupFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'Bangladeshi Authors', label: 'Bangladeshi' },
  { key: 'International Authors', label: 'International' },
  { key: 'Islamic Scholars', label: 'Islamic Scholars' },
];

interface Props {
  books: Book[];
  offlineById: Record<string, OfflineBookEntry>;
  onSelectAuthor: (authorPath: string[]) => void;
}

export function AuthorsScreen({ books, offlineById, onSelectAuthor }: Props) {
  const { theme, fs } = useAppTheme();
  const [query, setQuery] = useState('');
  const [selectedGroup, setSelectedGroup] = useState<GroupFilter>('all');
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [query, selectedGroup]);

  const authors = useMemo<AuthorItem[]>(() => {
    const map = new Map<string, MutableAuthorAcc>();

    for (const book of books) {
      if (book.cat !== 'Authors & Scholars' || !book.sub) continue;
      const parts = book.sub.split('/').filter(Boolean);
      if (parts.length < 2) continue;

      const topGroup = parts[0];
      let group: AuthorGroup;
      let authorName: string;
      let authorPath: string[];
      let subfolderName = '';

      if (topGroup === 'Bangladeshi Authors' || topGroup === 'International Authors') {
        group = topGroup;
        authorName = parts[1];
        authorPath = ['Authors & Scholars', parts[0], parts[1]];
        if (parts.length >= 3) subfolderName = parts[2];
      } else if (topGroup === 'Islamic Scholars') {
        group = 'Islamic Scholars';
        if (parts.length >= 3) {
          authorName = parts[2];
          authorPath = ['Authors & Scholars', parts[0], parts[1], parts[2]];
          if (parts.length >= 4) subfolderName = parts[3];
        } else {
          authorName = parts[1];
          authorPath = ['Authors & Scholars', parts[0], parts[1]];
        }
      } else {
        continue;
      }

      const key = authorPath.join('/');
      let acc = map.get(key);
      if (!acc) {
        acc = {
          key,
          name: authorName,
          group,
          path: authorPath,
          count: 0,
          offlineCount: 0,
          subfolders: new Set<string>(),
        };
        map.set(key, acc);
      }

      acc.count += 1;
      if (offlineById[book.id]) {
        acc.offlineCount += 1;
      }
      if (subfolderName) {
        acc.subfolders.add(subfolderName);
      }
    }

    const list: AuthorItem[] = [];
    for (const acc of map.values()) {
      list.push({
        key: acc.key,
        name: acc.name,
        group: acc.group,
        path: acc.path,
        count: acc.count,
        offlineCount: acc.offlineCount,
        subfolderCount: acc.subfolders.size,
      });
    }

    list.sort((a, b) =>
      a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' })
    );
    return list;
  }, [books, offlineById]);

  const filteredAuthors = useMemo(() => {
    const q = query.trim().toLowerCase();
    return authors.filter((item) => {
      if (selectedGroup !== 'all' && item.group !== selectedGroup) return false;
      if (q && !item.name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [authors, query, selectedGroup]);

  const visibleAuthors = useMemo(
    () => filteredAuthors.slice(0, visibleCount),
    [filteredAuthors, visibleCount]
  );

  const hasMore = filteredAuthors.length > visibleCount;

  const loadMore = useCallback(() => {
    setVisibleCount((n) =>
      n < filteredAuthors.length ? Math.min(filteredAuthors.length, n + PAGE_SIZE) : n
    );
  }, [filteredAuthors.length]);

  const renderAuthorCard = useCallback(
    ({ item }: { item: AuthorItem }) => (
      <TouchableOpacity
        style={[styles.authorCard, { backgroundColor: theme.surface, borderColor: theme.border }]}
        onPress={() => onSelectAuthor(item.path)}
        activeOpacity={0.84}
      >
        <AuthorAvatar name={item.name} size={64} />
        <Text style={[styles.authorCardName, { color: theme.ink, fontSize: fs(13) }]} numberOfLines={2}>
          {item.name}
        </Text>

        <View style={styles.badgesWrap}>
          <View style={[styles.miniPill, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
            <Text style={[styles.miniPillText, { color: theme.accent, fontSize: fs(10.5) }]}>
              {item.count.toLocaleString()} {item.count === 1 ? 'book' : 'books'}
              {item.offlineCount > 0 ? ` · ${item.offlineCount} saved` : ''}
            </Text>
          </View>

          {item.subfolderCount > 0 ? (
            <View style={[styles.miniPill, { backgroundColor: theme.accentSoft, borderColor: theme.accent }]}>
              <Text style={[styles.miniPillText, { color: theme.accent, fontSize: fs(10) }]}>
                {item.subfolderCount} {item.subfolderCount === 1 ? 'section' : 'sections'}
              </Text>
            </View>
          ) : null}
        </View>
      </TouchableOpacity>
    ),
    [theme, fs, onSelectAuthor]
  );

  return (
    <View style={[styles.root, { backgroundColor: theme.bg }]}>
      {/* Clean Header */}
      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.ink, fontSize: fs(23) }]}>Authors</Text>
        <View style={[styles.countPill, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
          <Text style={[styles.countPillText, { color: theme.accent, fontSize: fs(11.5) }]}>
            {filteredAuthors.length.toLocaleString()} authors
          </Text>
        </View>
      </View>

      {/* Instant Search Box */}
      <View style={styles.searchWrap}>
        <View style={[styles.searchBox, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
          <SearchIcon size={16} color={theme.muted} />
          <TextInput
            style={[styles.searchInput, { color: theme.ink, fontSize: fs(13) }]}
            placeholder="Search authors…"
            placeholderTextColor={theme.muted}
            value={query}
            onChangeText={setQuery}
          />
          {query ? (
            <TouchableOpacity onPress={() => setQuery('')} accessibilityLabel="Clear author search">
              <CloseIcon size={16} color={theme.muted} />
            </TouchableOpacity>
          ) : null}
        </View>
      </View>

      {/* Group Filter Chips */}
      <View style={styles.chipsOuter}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipsScroll}>
          {GROUP_FILTERS.map((gf) => {
            const active = selectedGroup === gf.key;
            return (
              <TouchableOpacity
                key={gf.key}
                style={[
                  styles.filterChip,
                  {
                    backgroundColor: active ? theme.cream : theme.surface,
                    borderColor: active ? theme.cream : theme.border,
                  },
                ]}
                onPress={() => setSelectedGroup(gf.key)}
                activeOpacity={0.84}
              >
                <Text
                  style={[
                    styles.filterChipText,
                    { color: active ? theme.creamInk : theme.cream, fontSize: fs(11.5) },
                    active && styles.filterChipTextActive,
                  ]}
                >
                  {gf.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>

      {/* Virtualized Scroll-and-Load 2-Column Authors Directory */}
      <FlatList
        style={styles.listRoot}
        data={visibleAuthors}
        keyExtractor={(item) => item.key}
        numColumns={2}
        columnWrapperStyle={styles.twoColRow}
        renderItem={renderAuthorCard}
        initialNumToRender={12}
        maxToRenderPerBatch={10}
        windowSize={7}
        removeClippedSubviews
        onEndReached={() => {
          if (hasMore) loadMore();
        }}
        onEndReachedThreshold={0.7}
        contentContainerStyle={styles.gridContent}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={
          <View style={styles.emptyBox}>
            <Text style={[styles.emptyTitle, { color: theme.ink, fontSize: fs(16) }]}>No authors found</Text>
            <Text style={[styles.emptySub, { color: theme.muted, fontSize: fs(12.5) }]}>
              Try a different spelling or switch to All authors.
            </Text>
          </View>
        }
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
    gap: 10,
  },
  title: { fontWeight: '800' },
  countPill: {
    borderWidth: 1,
    borderRadius: 14,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  countPillText: { fontWeight: '700' },
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
  chipsOuter: { marginTop: 10 },
  chipsScroll: {
    paddingHorizontal: 18,
    gap: 8,
    alignItems: 'center',
  },
  filterChip: {
    borderWidth: 1,
    borderRadius: 16,
    paddingHorizontal: 13,
    paddingVertical: 6,
  },
  filterChipText: { fontWeight: '600' },
  filterChipTextActive: { fontWeight: '800' },
  listRoot: { flex: 1, marginTop: 10 },
  gridContent: {
    paddingHorizontal: 18,
    paddingTop: 4,
    paddingBottom: 112,
    gap: 10,
  },
  twoColRow: {
    justifyContent: 'space-between',
  },
  authorCard: {
    width: '48.2%',
    borderRadius: 18,
    borderWidth: 1,
    padding: 12,
    alignItems: 'center',
    gap: 7,
  },
  authorCardName: {
    fontWeight: '700',
    textAlign: 'center',
    lineHeight: 17,
  },
  badgesWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 5,
  },
  miniPill: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  miniPillText: { fontWeight: '700' },
  emptyBox: { paddingVertical: 48, alignItems: 'center', gap: 6 },
  emptyTitle: { fontWeight: '700', textAlign: 'center' },
  emptySub: { textAlign: 'center', paddingHorizontal: 12, lineHeight: 17 },
});
