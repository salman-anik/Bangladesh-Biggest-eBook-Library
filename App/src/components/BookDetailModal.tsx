import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import { useAppTheme } from '../context/ThemeContext';
import { formatBytes } from '../services/libraryStore';
import type { Book, BookProgress, OfflineBookEntry } from '../types';
import { AuthorAvatar } from './AuthorAvatar';
import { BookCover } from './BookCover';
import {
  BookOpenIcon,
  BookmarkIcon,
  CheckCircleIcon,
  CloseIcon,
  DownloadIcon,
  OfflineIcon,
  TrashIcon,
} from './Icons';

interface Props {
  book: Book | null;
  progress?: BookProgress;
  offlineEntry?: OfflineBookEntry;
  isCurrentRead: boolean;
  isSaved: boolean;
  downloadingPct: number | null;
  onClose: () => void;
  onReadOnline: (book: Book) => void;
  onOpenOffline: (book: Book, entry: OfflineBookEntry) => void;
  onMakeOffline: (book: Book) => void;
  onRemoveOffline: (bookId: string) => void;
  onToggleSave: (bookId: string) => void;
  onSetCurrentlyReading: (bookId: string) => void;
  onUpdateProgress: (bookId: string, currentPage: number, totalPages: number) => void;
}

export function BookDetailModal({
  book,
  progress,
  offlineEntry,
  isCurrentRead,
  isSaved,
  downloadingPct,
  onClose,
  onReadOnline,
  onOpenOffline,
  onMakeOffline,
  onRemoveOffline,
  onToggleSave,
  onSetCurrentlyReading,
  onUpdateProgress,
}: Props) {
  const { theme, fs } = useAppTheme();
  const [currInput, setCurrInput] = useState('0');
  const [totalInput, setTotalInput] = useState('300');

  useEffect(() => {
    if (book) {
      setCurrInput(String(progress?.currentPage ?? 0));
      setTotalInput(String(progress?.totalPages ?? 300));
    }
  }, [book?.id, progress?.currentPage, progress?.totalPages]);

  if (!book) return null;

  const pct = progress?.progressPct ?? 0;

  return (
    <Modal visible={Boolean(book)} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={[styles.sheet, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
          <View style={[styles.handle, { backgroundColor: theme.border }]} />

          <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
            <View style={styles.topRow}>
              <BookCover
                book={book}
                localCoverUri={offlineEntry?.coverLocalUri}
                width={104}
                height={154}
                borderRadius={12}
                isOffline={Boolean(offlineEntry)}
              />
              <View style={styles.topInfo}>
                <Text style={[styles.catLabel, { color: theme.accent, fontSize: fs(11) }]} numberOfLines={1}>
                  {book.cat}
                  {book.sub ? ` / ${book.sub}` : ''}
                </Text>
                <Text style={[styles.title, { color: theme.ink, fontSize: fs(17) }]} numberOfLines={3}>
                  {book.title}
                </Text>
                <View style={styles.authorRow}>
                  <AuthorAvatar name={book.author} size={24} />
                  <Text style={[styles.author, { color: theme.muted, fontSize: fs(13) }]} numberOfLines={2}>
                    {book.author}
                  </Text>
                </View>
                <View style={styles.pillRow}>
                  <View style={[styles.metaPill, { backgroundColor: theme.surface }]}>
                    <Text style={[styles.metaPillText, { color: theme.cream }]}>{book.fmt}</Text>
                  </View>
                  <View style={[styles.metaPill, { backgroundColor: theme.surface }]}>
                    <Text style={[styles.metaPillText, { color: theme.cream }]}>{formatBytes(book.size)}</Text>
                  </View>
                  <View style={[styles.metaPill, { backgroundColor: theme.surface }]}>
                    <Text style={[styles.metaPillText, { color: theme.cream }]}>{book.lang}</Text>
                  </View>
                </View>
              </View>
            </View>

            {/* Primary Reading & Offline Actions */}
            <View style={styles.actionsStack}>
              {offlineEntry ? (
                <TouchableOpacity
                  style={[styles.primaryBtn, { backgroundColor: theme.cream }]}
                  onPress={() => onOpenOffline(book, offlineEntry)}
                  activeOpacity={0.85}
                >
                  <OfflineIcon size={18} color={theme.creamInk} />
                  <Text style={[styles.primaryBtnText, { color: theme.creamInk, fontSize: fs(14.5) }]}>
                    Open Offline ({book.fmt})
                  </Text>
                </TouchableOpacity>
              ) : null}

              <TouchableOpacity
                style={
                  offlineEntry
                    ? [styles.outlineBtn, { borderColor: theme.border, backgroundColor: theme.surface }]
                    : [styles.primaryBtn, { backgroundColor: theme.cream }]
                }
                onPress={() => onReadOnline(book)}
                activeOpacity={0.85}
              >
                <BookOpenIcon size={17} color={offlineEntry ? theme.ink : theme.creamInk} />
                <Text
                  style={
                    offlineEntry
                      ? [styles.outlineBtnText, { color: theme.ink, fontSize: fs(14) }]
                      : [styles.primaryBtnText, { color: theme.creamInk, fontSize: fs(14.5) }]
                  }
                >
                  Read Online
                </Text>
              </TouchableOpacity>

              {offlineEntry ? (
                <TouchableOpacity
                  style={[styles.dangerBtn, { borderColor: theme.danger }]}
                  onPress={() => onRemoveOffline(book.id)}
                  activeOpacity={0.8}
                >
                  <TrashIcon size={16} color={theme.danger} />
                  <Text style={[styles.dangerBtnText, { color: theme.danger, fontSize: fs(13) }]}>
                    Remove Offline ({formatBytes(offlineEntry.size)})
                  </Text>
                </TouchableOpacity>
              ) : downloadingPct !== null ? (
                <View style={[styles.downloadingBox, { backgroundColor: theme.surface }]}>
                  <ActivityIndicator color={theme.accent} size="small" />
                  <Text style={[styles.downloadingText, { color: theme.accent, fontSize: fs(13.5) }]}>
                    Saving offline… {downloadingPct}%
                  </Text>
                </View>
              ) : (
                <TouchableOpacity
                  style={[styles.terracottaBtn, { backgroundColor: theme.accent }]}
                  onPress={() => onMakeOffline(book)}
                  activeOpacity={0.85}
                >
                  <DownloadIcon size={18} color={theme.creamInk} />
                  <Text style={[styles.terracottaBtnText, { color: theme.creamInk, fontSize: fs(14.5) }]}>
                    Save Offline
                  </Text>
                </TouchableOpacity>
              )}
            </View>

            {/* Quick Bookmark & Set Currently Reading */}
            <View style={styles.secondaryRow}>
              <TouchableOpacity
                style={[
                  styles.halfBtn,
                  { backgroundColor: theme.surface, borderColor: theme.border },
                  isCurrentRead && { borderColor: theme.accent, backgroundColor: theme.accentSoft },
                ]}
                onPress={() => onSetCurrentlyReading(book.id)}
              >
                <CheckCircleIcon size={16} color={isCurrentRead ? theme.accent : theme.ink} />
                <Text style={[styles.halfBtnText, { color: theme.ink, fontSize: fs(12) }]}>
                  {isCurrentRead ? 'Reading' : 'Mark Current'}
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.halfBtn,
                  { backgroundColor: theme.surface, borderColor: theme.border },
                  isSaved && { borderColor: theme.accent, backgroundColor: theme.accentSoft },
                ]}
                onPress={() => onToggleSave(book.id)}
              >
                <BookmarkIcon size={16} color={isSaved ? theme.accent : theme.ink} filled={isSaved} />
                <Text style={[styles.halfBtnText, { color: theme.ink, fontSize: fs(12) }]}>
                  {isSaved ? 'Saved' : 'Bookmark'}
                </Text>
              </TouchableOpacity>
            </View>

            {/* Reading Progress Editor */}
            <View style={[styles.progressBox, { backgroundColor: theme.surface }]}>
              <View style={styles.progressHead}>
                <Text style={[styles.progressTitle, { color: theme.ink, fontSize: fs(13) }]}>Reading Progress</Text>
                <Text style={[styles.progressPct, { color: theme.accent, fontSize: fs(13) }]}>{pct}%</Text>
              </View>
              <View style={styles.inputRow}>
                <View style={styles.inputCol}>
                  <Text style={[styles.inputLabel, { color: theme.muted }]}>Page</Text>
                  <TextInput
                    style={[styles.input, { backgroundColor: theme.bg, borderColor: theme.border, color: theme.ink }]}
                    keyboardType="numeric"
                    value={currInput}
                    onChangeText={setCurrInput}
                  />
                </View>
                <View style={styles.inputCol}>
                  <Text style={[styles.inputLabel, { color: theme.muted }]}>Total</Text>
                  <TextInput
                    style={[styles.input, { backgroundColor: theme.bg, borderColor: theme.border, color: theme.ink }]}
                    keyboardType="numeric"
                    value={totalInput}
                    onChangeText={setTotalInput}
                  />
                </View>
                <TouchableOpacity
                  style={[styles.saveProgBtn, { backgroundColor: theme.cream }]}
                  onPress={() => {
                    const c = parseInt(currInput, 10) || 0;
                    const t = parseInt(totalInput, 10) || 300;
                    onUpdateProgress(book.id, c, t);
                  }}
                >
                  <Text style={[styles.saveProgBtnText, { color: theme.creamInk }]}>Save</Text>
                </TouchableOpacity>
              </View>
            </View>

            <TouchableOpacity style={styles.closeBtn} onPress={onClose}>
              <CloseIcon size={18} color={theme.muted} />
            </TouchableOpacity>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.72)',
    justifyContent: 'flex-end',
  },
  sheet: {
    borderTopLeftRadius: 26,
    borderTopRightRadius: 26,
    borderTopWidth: 1,
    maxHeight: '88%',
    paddingTop: 10,
  },
  handle: {
    width: 44,
    height: 4,
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 12,
  },
  scroll: {
    paddingHorizontal: 20,
    paddingBottom: 32,
    gap: 15,
  },
  topRow: { flexDirection: 'row', gap: 14 },
  topInfo: { flex: 1, gap: 6 },
  catLabel: { fontWeight: '700' },
  title: { fontWeight: '800', lineHeight: 23 },
  authorRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  author: { flex: 1 },
  pillRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 4 },
  metaPill: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  metaPillText: { fontSize: 11, fontWeight: '700' },
  actionsStack: { gap: 10 },
  primaryBtn: {
    borderRadius: 26,
    paddingVertical: 13,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  primaryBtnText: { fontWeight: '800' },
  terracottaBtn: {
    borderRadius: 26,
    paddingVertical: 13,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  terracottaBtnText: { fontWeight: '800' },
  outlineBtn: {
    borderWidth: 1,
    borderRadius: 26,
    paddingVertical: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  outlineBtnText: { fontWeight: '700' },
  dangerBtn: {
    borderWidth: 1,
    borderRadius: 26,
    paddingVertical: 11,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  dangerBtnText: { fontWeight: '700' },
  downloadingBox: {
    borderRadius: 26,
    paddingVertical: 13,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  downloadingText: { fontWeight: '700' },
  secondaryRow: { flexDirection: 'row', gap: 10 },
  halfBtn: {
    flex: 1,
    borderRadius: 14,
    borderWidth: 1,
    paddingVertical: 11,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  halfBtnText: { fontWeight: '700' },
  progressBox: { borderRadius: 16, padding: 14, gap: 10 },
  progressHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  progressTitle: { fontWeight: '700' },
  progressPct: { fontWeight: '800' },
  inputRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 8 },
  inputCol: { flex: 1, gap: 4 },
  inputLabel: { fontSize: 10, fontWeight: '600' },
  input: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 8,
    fontSize: 14,
    fontWeight: '700',
  },
  saveProgBtn: { borderRadius: 10, paddingHorizontal: 16, paddingVertical: 10 },
  saveProgBtnText: { fontSize: 13, fontWeight: '800' },
  closeBtn: { paddingVertical: 10, alignItems: 'center' },
});
