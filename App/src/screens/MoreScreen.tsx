import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Image,
  Linking,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import { BookCover } from '../components/BookCover';
import {
  BookOpenIcon,
  CloseIcon,
  GithubIcon,
  GlobeIcon,
  MailIcon,
  MoonIcon,
  RefreshIcon,
  SunIcon,
  TrashIcon,
  TypeIcon,
} from '../components/Icons';
import { useAppTheme } from '../context/ThemeContext';
import {
  type AppStorageUsage,
  type CatalogMeta,
  formatBytes,
  getAppStorageUsage,
} from '../services/libraryStore';
import { THEME_PRESETS } from '../theme';
import type { Book, FontScaleKey, OfflineBookEntry, ThemePresetKey } from '../types';

interface Props {
  books: Book[];
  catalogMeta: CatalogMeta;
  syncingCatalog: boolean;
  offlineById: Record<string, OfflineBookEntry>;
  onSyncCatalog: () => void;
  onClearCatalogCache: () => void;
  onOpenOfflineBook: (entry: OfflineBookEntry) => void;
  onRemoveOfflineBook: (bookId: string) => void;
}

const FONT_OPTIONS: { key: FontScaleKey; label: string }[] = [
  { key: 'small', label: 'Small' },
  { key: 'normal', label: 'Normal' },
  { key: 'large', label: 'Large' },
];

const PRESET_KEYS: ThemePresetKey[] = ['espresso', 'matcha', 'midnight', 'sepia', 'rosewood'];

export function MoreScreen({
  books,
  catalogMeta,
  syncingCatalog,
  offlineById,
  onSyncCatalog,
  onClearCatalogCache,
  onOpenOfflineBook,
  onRemoveOfflineBook,
}: Props) {
  const { theme, mode, preset, fontScale, fs, setThemeMode, setThemePreset, setFontScale } =
    useAppTheme();
  const [devModalOpen, setDevModalOpen] = useState(false);
  const [storage, setStorage] = useState<AppStorageUsage>({
    totalBytes: 0,
    catalogBytes: 0,
    offlineBooksBytes: 0,
    offlineCoversBytes: 0,
  });

  const offlineEntries = Object.values(offlineById);
  const byId = new Map(books.map((b) => [b.id, b]));

  useEffect(() => {
    let mounted = true;
    void getAppStorageUsage().then((u) => {
      if (mounted) setStorage(u);
    });
    return () => {
      mounted = false;
    };
  }, [offlineEntries.length, catalogMeta.syncedAt, catalogMeta.totalBooks]);

  const totalMem = Math.max(1, storage.totalBytes);
  const offlineBooksPct = Math.round((storage.offlineBooksBytes / totalMem) * 100);
  const catalogPct = Math.round((storage.catalogBytes / totalMem) * 100);

  return (
    <View style={[styles.root, { backgroundColor: theme.bg }]}>
      <ScrollView
        style={styles.root}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* Single Header Row: SETTINGS left + Top-Right Circular Developer Icon */}
        <View style={styles.headerRow}>
          <Text style={[styles.heading, { color: theme.ink, fontSize: fs(24) }]}>SETTINGS</Text>

          <TouchableOpacity
            style={[styles.devIconBtn, { borderColor: theme.accent, backgroundColor: theme.surface }]}
            onPress={() => setDevModalOpen(true)}
            activeOpacity={0.82}
            accessibilityLabel="Developer Info"
          >
            <Image
              source={require('../../assets/developer-profile.png')}
              style={styles.devTopPhoto}
              resizeMode="cover"
            />
          </TouchableOpacity>
        </View>

        {/* Appearance Card: Mode + Book App Themes + Font Size */}
        <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <Text style={[styles.cardTitle, { color: theme.ink, fontSize: fs(15) }]}>Appearance</Text>

          {/* Mode (Dark / White) */}
          <View style={styles.settingBlock}>
            <Text style={[styles.settingLabel, { color: theme.muted, fontSize: fs(11) }]}>Mode</Text>
            <View style={styles.segmentRow}>
              <TouchableOpacity
                style={[
                  styles.segmentBtn,
                  {
                    backgroundColor: mode === 'dark' ? theme.cream : theme.surfaceAlt,
                    borderColor: mode === 'dark' ? theme.cream : theme.border,
                  },
                ]}
                onPress={() => setThemeMode('dark')}
              >
                <MoonIcon size={16} color={mode === 'dark' ? theme.creamInk : theme.cream} />
                <Text
                  style={[
                    styles.segmentText,
                    { color: mode === 'dark' ? theme.creamInk : theme.cream, fontSize: fs(12) },
                  ]}
                >
                  Dark
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.segmentBtn,
                  {
                    backgroundColor: mode === 'light' ? theme.cream : theme.surfaceAlt,
                    borderColor: mode === 'light' ? theme.cream : theme.border,
                  },
                ]}
                onPress={() => setThemeMode('light')}
              >
                <SunIcon size={16} color={mode === 'light' ? theme.creamInk : theme.cream} />
                <Text
                  style={[
                    styles.segmentText,
                    { color: mode === 'light' ? theme.creamInk : theme.cream, fontSize: fs(12) },
                  ]}
                >
                  White
                </Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* Theme (5 Pinterest Book App Palettes) */}
          <View style={styles.settingBlock}>
            <Text style={[styles.settingLabel, { color: theme.muted, fontSize: fs(11) }]}>Theme</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.themeScroll}>
              {PRESET_KEYS.map((key) => {
                const p = THEME_PRESETS[key];
                const active = preset === key;
                return (
                  <TouchableOpacity
                    key={key}
                    style={[
                      styles.themeChip,
                      {
                        backgroundColor: active ? theme.accentSoft : theme.surfaceAlt,
                        borderColor: active ? theme.accent : theme.border,
                      },
                    ]}
                    onPress={() => setThemePreset(key)}
                    activeOpacity={0.84}
                  >
                    <View style={styles.swatchRow}>
                      {p.swatches.map((hex, i) => (
                        <View
                          key={`${key}-${i}`}
                          style={[styles.swatchDot, { backgroundColor: hex, borderColor: theme.border }]}
                        />
                      ))}
                    </View>
                    <Text
                      style={[
                        styles.themeLabel,
                        { color: active ? theme.accent : theme.cream, fontSize: fs(11.5) },
                        active && { fontWeight: '800' },
                      ]}
                    >
                      {p.label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </ScrollView>
          </View>

          {/* Font Size */}
          <View style={styles.settingBlock}>
            <View style={styles.labelInline}>
              <TypeIcon size={14} color={theme.muted} />
              <Text style={[styles.settingLabel, { color: theme.muted, fontSize: fs(11) }]}>Font Size</Text>
            </View>
            <View style={styles.segmentRow}>
              {FONT_OPTIONS.map((opt) => {
                const active = fontScale === opt.key;
                return (
                  <TouchableOpacity
                    key={opt.key}
                    style={[
                      styles.segmentBtn,
                      {
                        backgroundColor: active ? theme.accent : theme.surfaceAlt,
                        borderColor: active ? theme.accent : theme.border,
                      },
                    ]}
                    onPress={() => setFontScale(opt.key)}
                  >
                    <Text
                      style={[
                        styles.segmentText,
                        { color: active ? theme.creamInk : theme.cream, fontSize: fs(12) },
                      ]}
                    >
                      {opt.label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>
        </View>

        {/* App Memory / Local Storage Usage Card */}
        <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <View style={styles.cardHeadRow}>
            <Text style={[styles.cardTitle, { color: theme.ink, fontSize: fs(15) }]}>App Storage</Text>
            <Text style={[styles.storageTotal, { color: theme.accent, fontSize: fs(15) }]}>
              {storage.totalBytes > 0 ? formatBytes(storage.totalBytes) : '0 B'}
            </Text>
          </View>

          <View style={[styles.storageBar, { backgroundColor: theme.surfaceAlt }]}>
            {storage.offlineBooksBytes > 0 ? (
              <View style={{ width: `${Math.max(4, offlineBooksPct)}%`, height: '100%', backgroundColor: theme.accent }} />
            ) : null}
            {storage.catalogBytes > 0 ? (
              <View style={{ width: `${Math.max(4, catalogPct)}%`, height: '100%', backgroundColor: theme.sage }} />
            ) : null}
          </View>

          <View style={[styles.memMetaBox, { backgroundColor: theme.surfaceAlt, borderColor: theme.borderSubtle }]}>
            <View style={styles.memRow}>
              <View style={styles.memDotLabel}>
                <View style={[styles.dot, { backgroundColor: theme.accent }]} />
                <Text style={[styles.memLabel, { color: theme.cream, fontSize: fs(12) }]}>
                  Offline Books ({offlineEntries.length})
                </Text>
              </View>
              <Text style={[styles.memVal, { color: theme.ink, fontSize: fs(12) }]}>
                {storage.offlineBooksBytes > 0 ? formatBytes(storage.offlineBooksBytes) : '0 B'}
              </Text>
            </View>

            <View style={[styles.memDivider, { backgroundColor: theme.border }]} />

            <View style={styles.memRow}>
              <View style={styles.memDotLabel}>
                <View style={[styles.dot, { backgroundColor: theme.sage }]} />
                <Text style={[styles.memLabel, { color: theme.cream, fontSize: fs(12) }]}>
                  Catalog Cache
                </Text>
              </View>
              <Text style={[styles.memVal, { color: theme.ink, fontSize: fs(12) }]}>
                {storage.catalogBytes > 0 ? formatBytes(storage.catalogBytes) : 'Starter'}
              </Text>
            </View>

            <View style={[styles.memDivider, { backgroundColor: theme.border }]} />

            <View style={styles.memRow}>
              <View style={styles.memDotLabel}>
                <View style={[styles.dot, { backgroundColor: theme.muted }]} />
                <Text style={[styles.memLabel, { color: theme.cream, fontSize: fs(12) }]}>
                  Cached Covers
                </Text>
              </View>
              <Text style={[styles.memVal, { color: theme.ink, fontSize: fs(12) }]}>
                {storage.offlineCoversBytes > 0 ? formatBytes(storage.offlineCoversBytes) : '0 B'}
              </Text>
            </View>
          </View>
        </View>

        {/* Catalog Sync Card (Icon Buttons) */}
        <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <View style={styles.cardHeadRow}>
            <View style={{ flex: 1 }}>
              <Text style={[styles.cardTitle, { color: theme.ink, fontSize: fs(15) }]}>Library Catalog</Text>
              <Text style={[styles.cardSub, { color: theme.muted, fontSize: fs(11.5) }]}>
                {catalogMeta.source.toUpperCase()} · {books.length.toLocaleString()} indexed
              </Text>
            </View>

            <View style={styles.iconActionsRow}>
              <TouchableOpacity
                style={[styles.circleBtn, { backgroundColor: theme.cream }]}
                onPress={onSyncCatalog}
                disabled={syncingCatalog}
                accessibilityLabel="Sync Full Catalog"
              >
                {syncingCatalog ? (
                  <ActivityIndicator color={theme.creamInk} size="small" />
                ) : (
                  <RefreshIcon size={17} color={theme.creamInk} />
                )}
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.circleBtn, { backgroundColor: theme.surfaceAlt, borderWidth: 1, borderColor: theme.border }]}
                onPress={onClearCatalogCache}
                accessibilityLabel="Reset Cache"
              >
                <TrashIcon size={16} color={theme.danger} />
              </TouchableOpacity>
            </View>
          </View>
        </View>

        {/* Downloaded Offline Books */}
        <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <View style={styles.cardHeadRow}>
            <Text style={[styles.cardTitle, { color: theme.ink, fontSize: fs(15) }]}>
              Offline Books ({offlineEntries.length})
            </Text>
            <Text style={[styles.cardSize, { color: theme.accent, fontSize: fs(12) }]}>
              {storage.offlineBooksBytes > 0 ? formatBytes(storage.offlineBooksBytes) : ''}
            </Text>
          </View>

          {offlineEntries.length === 0 ? (
            <Text style={[styles.cardHint, { color: theme.muted, fontSize: fs(12) }]}>
              Tap download on any book or category to save for offline reading.
            </Text>
          ) : (
            <View style={styles.offlineList}>
              {offlineEntries.map((entry) => {
                const book: Book = byId.get(entry.bookId) || {
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
                return (
                  <View
                    key={entry.bookId}
                    style={[
                      styles.offlineItem,
                      { backgroundColor: theme.surfaceAlt, borderColor: theme.borderSubtle },
                    ]}
                  >
                    <BookCover
                      book={book}
                      localCoverUri={entry.coverLocalUri}
                      width={44}
                      height={64}
                      borderRadius={6}
                    />
                    <View style={styles.offlineInfo}>
                      <Text style={[styles.offlineTitle, { color: theme.ink, fontSize: fs(13) }]} numberOfLines={2}>
                        {entry.title}
                      </Text>
                      <Text style={[styles.offlineMeta, { color: theme.muted, fontSize: fs(11) }]}>
                        {entry.fmt} · {formatBytes(entry.size)}
                      </Text>
                    </View>
                    <TouchableOpacity
                      style={[styles.circleSmallBtn, { backgroundColor: theme.cream }]}
                      onPress={() => onOpenOfflineBook(entry)}
                      accessibilityLabel="Open offline book"
                    >
                      <BookOpenIcon size={15} color={theme.creamInk} />
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={[styles.circleSmallBtn, { backgroundColor: theme.surface, borderWidth: 1, borderColor: theme.border }]}
                      onPress={() => onRemoveOfflineBook(entry.bookId)}
                      accessibilityLabel="Remove offline book"
                    >
                      <TrashIcon size={14} color={theme.danger} />
                    </TouchableOpacity>
                  </View>
                );
              })}
            </View>
          )}
        </View>
      </ScrollView>

      {/* Developer Info & About Me Modal */}
      <Modal
        visible={devModalOpen}
        animationType="fade"
        transparent
        onRequestClose={() => setDevModalOpen(false)}
      >
        <View style={styles.modalBackdrop}>
          <View style={[styles.modalCard, { backgroundColor: theme.surface, borderColor: theme.border }]}>
            <View style={styles.modalTopRow}>
              <Text style={[styles.sectionEyebrow, { color: theme.accent }]}>DEVELOPER &amp; ABOUT ME</Text>
              <TouchableOpacity
                style={[styles.closeCircle, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
                onPress={() => setDevModalOpen(false)}
              >
                <CloseIcon size={16} color={theme.ink} />
              </TouchableOpacity>
            </View>

            <View style={styles.devProfileRow}>
              <Image
                source={require('../../assets/developer-profile.png')}
                style={[styles.devAvatar, { borderColor: theme.accent, backgroundColor: theme.surfaceAlt }]}
                resizeMode="cover"
              />
              <View style={styles.devIdentity}>
                <Text style={[styles.devName, { color: theme.ink, fontSize: fs(19) }]}>Salman Anik</Text>
                <Text style={[styles.devTagline, { color: theme.cream, fontSize: fs(12) }]}>
                  CSE Student · Data Science Enthusiast · Python Developer
                </Text>
              </View>
            </View>

            <Text style={[styles.devBio, { color: theme.muted, fontSize: fs(12.5) }]}>
              Computer Science &amp; Engineering student at East West University, Dhaka, focused on
              Python, SQL, Data Science, and building practical open-source projects—including
              Bangladesh&apos;s Biggest eBook Library and AnaPharm.
            </Text>

            <View style={[styles.devMetaBox, { backgroundColor: theme.surfaceAlt, borderColor: theme.borderSubtle }]}>
              <View style={styles.devMetaRow}>
                <Text style={[styles.devMetaLabel, { color: theme.muted }]}>University</Text>
                <Text style={[styles.devMetaValue, { color: theme.ink }]}>East West University (B.Sc. in CSE)</Text>
              </View>
              <View style={[styles.devMetaDivider, { backgroundColor: theme.border }]} />
              <View style={styles.devMetaRow}>
                <Text style={[styles.devMetaLabel, { color: theme.muted }]}>Location</Text>
                <Text style={[styles.devMetaValue, { color: theme.ink }]}>Dhaka, Bangladesh</Text>
              </View>
            </View>

            <View style={styles.devLinksRow}>
              <TouchableOpacity
                style={[styles.devLinkPrimary, { backgroundColor: theme.accent }]}
                onPress={() => void Linking.openURL('https://salmananik.vercel.app/')}
                activeOpacity={0.85}
              >
                <GlobeIcon size={16} color={theme.creamInk} />
                <Text style={[styles.devLinkPrimaryText, { color: theme.creamInk }]}>Portfolio</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.devLinkSecondary, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
                onPress={() => void Linking.openURL('https://github.com/salman-anik')}
                activeOpacity={0.85}
              >
                <GithubIcon size={16} color={theme.cream} />
                <Text style={[styles.devLinkSecondaryText, { color: theme.cream }]}>GitHub</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.devLinkSecondary, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
                onPress={() => void Linking.openURL('mailto:salmananik.bd@gmail.com')}
                activeOpacity={0.85}
              >
                <MailIcon size={16} color={theme.cream} />
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  content: { paddingHorizontal: 18, paddingTop: 12, paddingBottom: 112, gap: 15 },
  headerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  heading: { fontWeight: '800' },
  devIconBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    borderWidth: 2,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
  devTopPhoto: { width: '100%', height: '100%' },
  card: {
    borderRadius: 20,
    padding: 16,
    borderWidth: 1,
    gap: 12,
  },
  cardHeadRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 10 },
  cardTitle: { fontWeight: '800' },
  cardSize: { fontWeight: '700' },
  cardSub: { fontWeight: '600', marginTop: 2 },
  cardHint: { lineHeight: 18 },
  settingBlock: { gap: 7 },
  labelInline: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  settingLabel: { fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },
  segmentRow: { flexDirection: 'row', gap: 8 },
  segmentBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderRadius: 14,
    borderWidth: 1,
    paddingVertical: 9,
  },
  segmentText: { fontWeight: '700' },
  themeScroll: { gap: 8, paddingRight: 6 },
  themeChip: {
    borderWidth: 1.5,
    borderRadius: 14,
    paddingHorizontal: 11,
    paddingVertical: 8,
    alignItems: 'center',
    gap: 6,
    minWidth: 82,
  },
  swatchRow: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  swatchDot: { width: 13, height: 13, borderRadius: 7, borderWidth: 1 },
  themeLabel: { fontWeight: '600' },
  storageTotal: { fontWeight: '800' },
  storageBar: {
    height: 8,
    borderRadius: 4,
    overflow: 'hidden',
    flexDirection: 'row',
  },
  memMetaBox: {
    borderRadius: 14,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 8,
    gap: 7,
  },
  memRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  memDotLabel: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  memLabel: { fontWeight: '600' },
  memVal: { fontWeight: '800' },
  memDivider: { height: StyleSheet.hairlineWidth },
  iconActionsRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  circleBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: 'center',
    justifyContent: 'center',
  },
  offlineList: { gap: 9 },
  offlineItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    borderRadius: 12,
    padding: 9,
    borderWidth: 1,
  },
  offlineInfo: { flex: 1, gap: 2 },
  offlineTitle: { fontWeight: '700' },
  offlineMeta: {},
  circleSmallBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.68)',
    justifyContent: 'center',
    paddingHorizontal: 20,
  },
  modalCard: {
    borderRadius: 24,
    borderWidth: 1,
    padding: 18,
    gap: 14,
  },
  modalTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  sectionEyebrow: {
    fontSize: 10.5,
    fontWeight: '800',
    letterSpacing: 0.9,
  },
  closeCircle: {
    width: 32,
    height: 32,
    borderRadius: 16,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  devProfileRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  devAvatar: {
    width: 68,
    height: 68,
    borderRadius: 34,
    borderWidth: 2,
  },
  devIdentity: { flex: 1, gap: 3 },
  devName: { fontWeight: '800' },
  devTagline: { fontWeight: '600', lineHeight: 17 },
  devBio: { lineHeight: 19 },
  devMetaBox: {
    borderRadius: 14,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 8,
    gap: 7,
  },
  devMetaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
  },
  devMetaLabel: { fontSize: 11, fontWeight: '700' },
  devMetaValue: { fontSize: 11.5, fontWeight: '700', flexShrink: 1, textAlign: 'right' },
  devMetaDivider: { height: StyleSheet.hairlineWidth },
  devLinksRow: { flexDirection: 'row', gap: 8 },
  devLinkPrimary: {
    flex: 1.4,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderRadius: 14,
    paddingVertical: 11,
  },
  devLinkPrimaryText: { fontSize: 12.5, fontWeight: '800' },
  devLinkSecondary: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderWidth: 1,
    borderRadius: 14,
    paddingVertical: 11,
  },
  devLinkSecondaryText: { fontSize: 12, fontWeight: '700' },
});
