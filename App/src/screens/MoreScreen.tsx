import React, { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Linking,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import {
  ChevronRightIcon,
  CloseIcon,
  FlameIcon,
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
import { CURRENT_APP_VERSION, type AppUpdateInfo } from '../services/updateService';
import { THEME_PRESETS } from '../theme';
import type {
  Book,
  BookProgress,
  FontScaleKey,
  OfflineBookEntry,
  ReadingStreak,
  ThemePresetKey,
} from '../types';
import { DeveloperScreen } from './DeveloperScreen';
import { StatsScreen } from './StatsScreen';
import { useHorizontalScrollLock } from '../utils/horizontalScrollLock';

interface Props {
  books: Book[];
  catalogMeta: CatalogMeta;
  syncingCatalog: boolean;
  offlineById: Record<string, OfflineBookEntry>;
  progressById: Record<string, BookProgress>;
  savedIds: string[];
  streak: ReadingStreak;
  updateInfo: AppUpdateInfo | null;
  checkingUpdate: boolean;
  onSyncCatalog: () => void;
  onClearCatalogCache: () => void;
  onCheckUpdate: () => void;
  onOpenUpdateModal?: () => void;
  onSelectCategory: (cat: string) => void;
  onOpenBookDetail: (book: Book) => void;
  onHorizontalTouchLock?: (locked: boolean) => void;
}

const FONT_OPTIONS: { key: FontScaleKey; label: string }[] = [
  { key: 'small', label: 'Small' },
  { key: 'normal', label: 'Normal' },
  { key: 'large', label: 'Large' },
];

const PRESET_KEYS: ThemePresetKey[] = ['espresso', 'matcha', 'midnight', 'sepia', 'rosewood'];

export const MoreScreen = React.memo(function MoreScreen({
  books,
  catalogMeta,
  syncingCatalog,
  offlineById,
  progressById,
  savedIds,
  streak,
  updateInfo,
  checkingUpdate,
  onSyncCatalog,
  onClearCatalogCache,
  onCheckUpdate,
  onOpenUpdateModal,
  onSelectCategory,
  onOpenBookDetail,
  onHorizontalTouchLock,
}: Props) {
  const { theme, mode, preset, fontScale, fs, setThemeMode, setThemePreset, setFontScale } =
    useAppTheme();
  const hLockProps = useHorizontalScrollLock(onHorizontalTouchLock);
  const [devModalOpen, setDevModalOpen] = useState(false);
  const [statsModalOpen, setStatsModalOpen] = useState(false);
  const [storage, setStorage] = useState<AppStorageUsage>({
    totalBytes: 0,
    catalogBytes: 0,
    offlineBooksBytes: 0,
    offlineCoversBytes: 0,
  });

  const offlineEntries = Object.values(offlineById);

  const readingSummary = useMemo(() => {
    let completedCount = 0;
    let inProgressCount = 0;
    for (const p of Object.values(progressById)) {
      if (p.progressPct >= 100) completedCount++;
      else if (p.progressPct > 0 || p.currentPage > 0) inProgressCount++;
    }
    return { completedCount, inProgressCount };
  }, [progressById]);

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
        {/* Single Clean Header */}
        <Text style={[styles.heading, { color: theme.ink, fontSize: fs(24) }]}>SETTINGS</Text>

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
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.themeScroll} {...hLockProps}>
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

        {/* Reading Stats Card */}
        <TouchableOpacity
          style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}
          onPress={() => setStatsModalOpen(true)}
          activeOpacity={0.84}
        >
          <View style={styles.cardHeadRow}>
            <Text style={[styles.cardTitle, { color: theme.ink, fontSize: fs(15) }]}>Reading Stats</Text>
            <View style={styles.statsLinkRow}>
              <Text style={[styles.statsLinkText, { color: theme.accent, fontSize: fs(12) }]}>
                View Full Stats
              </Text>
              <ChevronRightIcon size={16} color={theme.accent} />
            </View>
          </View>

          <View style={styles.statsPillsRow}>
            <View style={[styles.statPill, { backgroundColor: theme.surfaceAlt, borderColor: theme.borderSubtle }]}>
              <FlameIcon size={14} color={theme.accent} />
              <Text style={[styles.statPillVal, { color: theme.ink, fontSize: fs(12) }]}>
                {streak.days}d streak
              </Text>
            </View>

            <View style={[styles.statPill, { backgroundColor: theme.surfaceAlt, borderColor: theme.borderSubtle }]}>
              <Text style={[styles.statPillVal, { color: theme.ink, fontSize: fs(12) }]}>
                {readingSummary.inProgressCount} active · {readingSummary.completedCount} done
              </Text>
            </View>

            <View style={[styles.statPill, { backgroundColor: theme.surfaceAlt, borderColor: theme.borderSubtle }]}>
              <Text style={[styles.statPillVal, { color: theme.cream, fontSize: fs(12) }]}>
                {savedIds.length} saved
              </Text>
            </View>
          </View>
        </TouchableOpacity>

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

        {/* App Updates Card */}
        <View style={[styles.card, { backgroundColor: theme.surface, borderColor: updateInfo?.hasUpdate ? theme.accent : theme.border }]}>
          <View style={styles.cardHeadRow}>
            <View style={{ flex: 1, gap: 2 }}>
              <Text style={[styles.cardTitle, { color: theme.ink, fontSize: fs(15) }]}>App Updates</Text>
              <Text style={[styles.cardSub, { color: updateInfo?.hasUpdate ? theme.accent : theme.muted, fontSize: fs(11.5) }]}>
                {updateInfo?.hasUpdate
                  ? `New version v${updateInfo.latestVersion} available!`
                  : `Installed: v${CURRENT_APP_VERSION} · ${updateInfo?.error ? 'Check unavailable' : 'Up to date'}`}
              </Text>
            </View>

            <View style={styles.updateBtnsRow}>
              <TouchableOpacity
                style={[styles.checkUpdateBtn, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
                onPress={onCheckUpdate}
                disabled={checkingUpdate}
                activeOpacity={0.82}
              >
                {checkingUpdate ? (
                  <ActivityIndicator size="small" color={theme.accent} />
                ) : (
                  <Text style={[styles.checkUpdateText, { color: theme.ink, fontSize: fs(11.5) }]}>
                    Check for Updates
                  </Text>
                )}
              </TouchableOpacity>

              {updateInfo?.hasUpdate ? (
                <TouchableOpacity
                  style={[styles.updateNowBtn, { backgroundColor: theme.accent }]}
                  onPress={onOpenUpdateModal ? onOpenUpdateModal : () => void Linking.openURL(updateInfo.downloadUrl)}
                  activeOpacity={0.85}
                >
                  <Text style={[styles.updateNowText, { color: theme.creamInk, fontSize: fs(11.5) }]}>
                    Update Now
                  </Text>
                </TouchableOpacity>
              ) : null}
            </View>
          </View>
          {updateInfo?.hasUpdate && updateInfo.releaseNotes ? (
            <Text style={[styles.cardHint, { color: theme.muted, fontSize: fs(11.5) }]}>
              {updateInfo.releaseNotes}
            </Text>
          ) : null}
        </View>

        {/* Developer, Privacy Policy & Copyright Card */}
        <TouchableOpacity
          style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}
          onPress={() => setDevModalOpen(true)}
          activeOpacity={0.84}
        >
          <View style={styles.cardHeadRow}>
            <View style={{ flex: 1, gap: 2 }}>
              <Text style={[styles.cardTitle, { color: theme.ink, fontSize: fs(15) }]}>
                Developer, Privacy Policy &amp; Copyright
              </Text>
              <Text style={[styles.cardSub, { color: theme.muted, fontSize: fs(11.5) }]}>
                Salman Anik · Data policy, DMCA &amp; license notice
              </Text>
            </View>
            <ChevronRightIcon size={18} color={theme.accent} />
          </View>
        </TouchableOpacity>
      </ScrollView>

      {/* Full Reading Stats Modal */}
      <Modal
        visible={statsModalOpen}
        animationType="slide"
        onRequestClose={() => setStatsModalOpen(false)}
      >
        <SafeAreaView style={[styles.statsModalRoot, { backgroundColor: theme.bg }]} edges={['top', 'bottom']}>
          <View style={[styles.statsModalHeader, { borderBottomColor: theme.border }]}>
            <Text style={[styles.statsModalTitle, { color: theme.ink, fontSize: fs(20) }]}>
              Reading Stats
            </Text>
            <TouchableOpacity
              style={[styles.closeCircle, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
              onPress={() => setStatsModalOpen(false)}
              accessibilityLabel="Close reading stats"
            >
              <CloseIcon size={16} color={theme.ink} />
            </TouchableOpacity>
          </View>

          <StatsScreen
            books={books}
            progressById={progressById}
            savedIds={savedIds}
            offlineById={offlineById}
            streak={streak}
            hideHeader
            onSelectCategory={(cat) => {
              setStatsModalOpen(false);
              onSelectCategory(cat);
            }}
            onOpenBookDetail={(b) => {
              setStatsModalOpen(false);
              onOpenBookDetail(b);
            }}
          />
        </SafeAreaView>
      </Modal>

      {/* Developer Info, Privacy Policy & Copyright Screen */}
      <DeveloperScreen visible={devModalOpen} onClose={() => setDevModalOpen(false)} />
    </View>
  );
});

const styles = StyleSheet.create({
  root: { flex: 1 },
  content: { paddingHorizontal: 18, paddingTop: 12, paddingBottom: 112, gap: 15 },
  heading: { fontWeight: '800' },
  card: {
    borderRadius: 20,
    padding: 16,
    borderWidth: 1,
    gap: 12,
  },
  cardHeadRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 10 },
  cardTitle: { fontWeight: '800' },
  statsLinkRow: { flexDirection: 'row', alignItems: 'center', gap: 3 },
  statsLinkText: { fontWeight: '700' },
  statsPillsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  statPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    borderRadius: 12,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  statPillVal: { fontWeight: '700' },
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
  updateBtnsRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  checkUpdateBtn: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 11,
    paddingVertical: 7,
    minWidth: 118,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkUpdateText: { fontWeight: '700' },
  updateNowBtn: {
    borderRadius: 12,
    paddingHorizontal: 11,
    paddingVertical: 7,
    alignItems: 'center',
    justifyContent: 'center',
  },
  updateNowText: { fontWeight: '800' },
  statsModalRoot: { flex: 1 },
  statsModalHeader: {
    paddingHorizontal: 18,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  statsModalTitle: { fontWeight: '800' },
  closeCircle: {
    width: 32,
    height: 32,
    borderRadius: 16,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
