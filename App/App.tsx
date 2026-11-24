import { StatusBar } from 'expo-status-bar';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  BackHandler,
  Image,
  Linking,
  type NativeScrollEvent,
  type NativeSyntheticEvent,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';

import { BookDetailModal } from './src/components/BookDetailModal';
import { BottomNavBar } from './src/components/BottomNavBar';
import { CloseIcon } from './src/components/Icons';
import { ReaderModal } from './src/components/ReaderModal';
import { ThemeProvider } from './src/context/ThemeContext';
import { ExploreScreen } from './src/screens/ExploreScreen';
import { HomeScreen } from './src/screens/HomeScreen';
import { LibraryScreen } from './src/screens/LibraryScreen';
import { MoreScreen } from './src/screens/MoreScreen';
import { SearchScreen } from './src/screens/SearchScreen';
import {
  bumpDailyStreak,
  type CatalogMeta,
  clearCatalogCache,
  downloadBookOffline,
  formatBytes,
  getDefaultState,
  loadCachedOrStarterCatalog,
  loadPersistedState,
  openOfflineBookFile,
  removeOfflineBook,
  savePersistedState,
  syncRemoteCatalog,
  updateProgressMap,
} from './src/services/libraryStore';
import { type AppUpdateInfo, checkForAppUpdate } from './src/services/updateService';
import { THEME_PRESETS } from './src/theme';
import type {
  AppPersistedState,
  BatchDownloadStatus,
  Book,
  FontScaleKey,
  OfflineBookEntry,
  TabKey,
  ThemeMode,
  ThemePresetKey,
} from './src/types';

const TAB_ORDER: TabKey[] = ['home', 'library', 'explore', 'search', 'more'];

function MainApp() {
  const insets = useSafeAreaInsets();
  const { width: windowWidth } = useWindowDimensions();
  const pagerRef = useRef<React.ComponentRef<typeof ScrollView> | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>('home');
  const [visitedTabs, setVisitedTabs] = useState<TabKey[]>(['home', 'library']);
  const [pagerLocked, setPagerLocked] = useState(false);
  const handleHorizontalTouchLock = useCallback((locked: boolean) => {
    pagerRef.current?.setNativeProps({ scrollEnabled: !locked });
    setPagerLocked(locked);
  }, []);
  const [books, setBooks] = useState<Book[]>([]);
  const [catalogMeta, setCatalogMeta] = useState<CatalogMeta>({
    source: 'starter',
    syncedAt: 'Loading…',
    totalBooks: 0,
    totalBytes: 0,
    coversCount: 0,
    authorsCount: 0,
    driveRoots: {},
    cats: [],
  });
  const [appState, setAppState] = useState<AppPersistedState>(getDefaultState);
  const [booting, setBooting] = useState(true);
  const [syncingCatalog, setSyncingCatalog] = useState(false);
  const [downloadingMap, setDownloadingMap] = useState<Record<string, number>>({});
  const [batchDownload, setBatchDownload] = useState<BatchDownloadStatus | null>(null);
  const batchCancelRef = useRef(false);

  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedSubcategory, setSelectedSubcategory] = useState<string>('');
  const [explorePath, setExplorePath] = useState<string[]>([]);
  const [detailBook, setDetailBook] = useState<Book | null>(null);
  const [readerBook, setReaderBook] = useState<Book | null>(null);
  const [updateInfo, setUpdateInfo] = useState<AppUpdateInfo | null>(null);
  const [checkingUpdate, setCheckingUpdate] = useState(false);
  const [updateBannerDismissed, setUpdateBannerDismissed] = useState(false);

  const themeMode: ThemeMode = appState.themeMode === 'dark' ? 'dark' : 'light';
  const themePreset: ThemePresetKey =
    appState.themePreset && THEME_PRESETS[appState.themePreset] ? appState.themePreset : 'espresso';
  const fontScale: FontScaleKey = appState.fontScale || 'normal';
  const activeTheme = THEME_PRESETS[themePreset][themeMode];

  const persist = useCallback((updater: (prev: AppPersistedState) => AppPersistedState) => {
    setAppState((prev) => {
      const next = updater(prev);
      void savePersistedState(next);
      return next;
    });
  }, []);

  const ensureTabVisited = useCallback((tab: TabKey) => {
    const idx = TAB_ORDER.indexOf(tab);
    const needed = [tab];
    if (idx > 0) needed.push(TAB_ORDER[idx - 1]);
    if (idx >= 0 && idx < TAB_ORDER.length - 1) needed.push(TAB_ORDER[idx + 1]);
    setVisitedTabs((prev) => {
      if (needed.every((t) => prev.includes(t))) return prev;
      const merged = [...prev];
      for (const t of needed) {
        if (!merged.includes(t)) merged.push(t);
      }
      return merged;
    });
  }, []);

  const navigateToTab = useCallback(
    (nextTab: TabKey, resetExploreIfSame = false) => {
      if (resetExploreIfSame && nextTab === 'explore' && activeTab === 'explore') {
        setExplorePath([]);
      }
      setActiveTab(nextTab);
      ensureTabVisited(nextTab);
      const idx = TAB_ORDER.indexOf(nextTab);
      if (idx >= 0) {
        pagerRef.current?.scrollTo({ x: idx * windowWidth, animated: true });
      }
    },
    [activeTab, ensureTabVisited, windowWidth]
  );

  useEffect(() => {
    if (!booting) {
      const idx = TAB_ORDER.indexOf(activeTab);
      if (idx >= 0) {
        pagerRef.current?.scrollTo({ x: idx * windowWidth, animated: false });
      }
    }
  }, [windowWidth, booting]);

  const handlePagerMomentumEnd = useCallback(
    (e: NativeSyntheticEvent<NativeScrollEvent>) => {
      const x = e.nativeEvent.contentOffset.x;
      const idx = Math.max(0, Math.min(TAB_ORDER.length - 1, Math.round(x / Math.max(windowWidth, 1))));
      const next = TAB_ORDER[idx];
      if (next) {
        setActiveTab(next);
        ensureTabVisited(next);
      }
    },
    [windowWidth, ensureTabVisited]
  );

  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      if (readerBook) {
        setReaderBook(null);
        return true;
      }
      if (detailBook) {
        setDetailBook(null);
        return true;
      }
      if (activeTab === 'explore' && explorePath.length > 0) {
        setExplorePath((p) => p.slice(0, -1));
        return true;
      }
      if (activeTab !== 'home') {
        navigateToTab('home');
        return true;
      }
      return false;
    });
    return () => sub.remove();
  }, [readerBook, detailBook, activeTab, explorePath.length, navigateToTab]);

  useEffect(() => {
    let mounted = true;
    async function boot() {
      const [catRes, st] = await Promise.all([loadCachedOrStarterCatalog(), loadPersistedState()]);
      if (!mounted) return;
      setBooks(catRes.books);
      setCatalogMeta(catRes.meta);
      setAppState(st);
      setBooting(false);

      // Background sync full 22,166 catalog if currently on starter pack
      if (catRes.meta.source === 'starter') {
        setSyncingCatalog(true);
        try {
          const fresh = await syncRemoteCatalog();
          if (mounted) {
            setBooks(fresh.books);
            setCatalogMeta(fresh.meta);
          }
        } catch {
          // Offline on boot: keep starter pack silently
        } finally {
          if (mounted) setSyncingCatalog(false);
        }
      }
    }
    void boot();
    return () => {
      mounted = false;
    };
  }, []);

  const currentlyReading = useMemo(() => {
    if (!books.length || !appState.currentlyReadingId) return null;
    return books.find((b) => b.id === appState.currentlyReadingId) || null;
  }, [books, appState.currentlyReadingId]);

  const markReadActivity = useCallback(
    (bookId: string) => {
      persist((prev) => ({
        ...prev,
        currentlyReadingId: bookId,
        streak: bumpDailyStreak(prev.streak),
      }));
    },
    [persist]
  );

  const handleOpenOffline = useCallback(
    async (book: Book, entry: OfflineBookEntry) => {
      markReadActivity(book.id);
      const upper = book.fmt.toUpperCase();
      if (['JPG', 'JPEG', 'PNG', 'TXT', 'MD'].includes(upper)) {
        setDetailBook(null);
        setReaderBook(book);
        return;
      }
      try {
        await openOfflineBookFile(entry);
      } catch (err) {
        Alert.alert('Open Offline Failed', err instanceof Error ? err.message : String(err));
      }
    },
    [markReadActivity]
  );

  const handleReadOnline = useCallback(
    (book: Book) => {
      markReadActivity(book.id);
      setDetailBook(null);
      setReaderBook(book);
    },
    [markReadActivity]
  );

  const handleQuickRead = useCallback(
    (book: Book) => {
      const offline = appState.offlineById[book.id];
      if (offline) {
        void handleOpenOffline(book, offline);
      } else {
        handleReadOnline(book);
      }
    },
    [appState.offlineById, handleOpenOffline, handleReadOnline]
  );

  const handleMakeOffline = useCallback(
    async (book: Book) => {
      if (downloadingMap[book.id] !== undefined) return;
      setDownloadingMap((m) => ({ ...m, [book.id]: 1 }));
      try {
        const entry = await downloadBookOffline(book, (pct) => {
          setDownloadingMap((m) => ({ ...m, [book.id]: pct }));
        });
        persist((prev) => ({
          ...prev,
          offlineById: { ...prev.offlineById, [book.id]: entry },
        }));
      } catch (err) {
        Alert.alert(
          'Offline Download Failed',
          err instanceof Error ? err.message : 'Unable to download book for offline use.'
        );
      } finally {
        setDownloadingMap((m) => {
          const next = { ...m };
          delete next[book.id];
          return next;
        });
      }
    },
    [downloadingMap, persist]
  );

  const handleDownloadFolderOffline = useCallback(
    (folderName: string, folderBooks: Book[]) => {
      if (batchDownload) {
        Alert.alert('Download in Progress', 'Please wait or cancel the current section download first.');
        return;
      }
      const remaining = folderBooks.filter((b) => !appState.offlineById[b.id]);
      if (remaining.length === 0) {
        Alert.alert('Already Offline', `All books in "${folderName}" are already saved offline.`);
        return;
      }
      const totalBytes = remaining.reduce((s, b) => s + (b.size || 0), 0);

      const runBatch = async () => {
        batchCancelRef.current = false;
        let completed = 0;
        let failed = 0;

        setBatchDownload({
          folderName,
          total: remaining.length,
          completed: 0,
          failed: 0,
          currentTitle: remaining[0]?.title || '',
        });

        for (const book of remaining) {
          if (batchCancelRef.current) break;

          setBatchDownload({
            folderName,
            total: remaining.length,
            completed,
            failed,
            currentTitle: book.title,
          });
          setDownloadingMap((m) => ({ ...m, [book.id]: 1 }));

          try {
            const entry = await downloadBookOffline(book, (pct) => {
              setDownloadingMap((m) => ({ ...m, [book.id]: pct }));
            });
            completed++;
            persist((prev) => ({
              ...prev,
              offlineById: { ...prev.offlineById, [book.id]: entry },
            }));
          } catch {
            failed++;
          } finally {
            setDownloadingMap((m) => {
              const next = { ...m };
              delete next[book.id];
              return next;
            });
          }
        }

        const cancelled = batchCancelRef.current;
        setBatchDownload(null);

        Alert.alert(
          cancelled ? 'Section Download Stopped' : 'Section Saved Offline',
          cancelled
            ? `Saved ${completed} of ${remaining.length} books from "${folderName}" before cancelling.`
            : `Saved ${completed} book${completed === 1 ? '' : 's'} from "${folderName}" offline${
                failed > 0 ? ` (${failed} skipped due to network error)` : ''
              }.`
        );
      };

      Alert.alert(
        `Download Full "${folderName}"?`,
        `This will download ${remaining.length.toLocaleString()} book${remaining.length === 1 ? '' : 's'} (${formatBytes(totalBytes)}) for offline reading.`,
        [
          { text: 'Cancel', style: 'cancel' },
          { text: 'Download All', onPress: () => void runBatch() },
        ]
      );
    },
    [appState.offlineById, batchDownload, persist]
  );

  const handleCancelBatchDownload = useCallback(() => {
    batchCancelRef.current = true;
  }, []);

  const handleRemoveOffline = useCallback(
    async (bookId: string) => {
      const entry = appState.offlineById[bookId];
      if (entry) {
        await removeOfflineBook(entry);
      }
      persist((prev) => {
        const nextOffline = { ...prev.offlineById };
        delete nextOffline[bookId];
        return { ...prev, offlineById: nextOffline };
      });
    },
    [appState.offlineById, persist]
  );

  const handleToggleSave = useCallback(
    (bookId: string) => {
      persist((prev) => {
        const has = prev.savedIds.includes(bookId);
        const savedIds = has
          ? prev.savedIds.filter((id) => id !== bookId)
          : [bookId, ...prev.savedIds];
        return { ...prev, savedIds };
      });
    },
    [persist]
  );

  const handleSetCurrentlyReading = useCallback(
    (bookId: string) => {
      markReadActivity(bookId);
    },
    [markReadActivity]
  );

  const handleUpdateProgress = useCallback(
    (bookId: string, currentPage: number, totalPages: number) => {
      persist((prev) => ({
        ...prev,
        currentlyReadingId: bookId,
        progressById: updateProgressMap(prev.progressById, bookId, currentPage, totalPages),
        streak: bumpDailyStreak(prev.streak),
      }));
    },
    [persist]
  );

  const handleRemoveFromReading = useCallback(
    (bookId: string) => {
      persist((prev) => {
        const nextProgress = { ...prev.progressById };
        delete nextProgress[bookId];
        let nextCurrent = prev.currentlyReadingId;
        if (prev.currentlyReadingId === bookId) {
          const remaining = Object.values(nextProgress).sort((a, b) =>
            (b.updatedAt || '').localeCompare(a.updatedAt || '')
          );
          nextCurrent = remaining[0]?.bookId || null;
        }
        return {
          ...prev,
          currentlyReadingId: nextCurrent,
          progressById: nextProgress,
        };
      });
    },
    [persist]
  );

  const handleCheckUpdate = useCallback(async (manual: boolean) => {
    setCheckingUpdate(true);
    try {
      const info = await checkForAppUpdate();
      setUpdateInfo(info);
      if (info.hasUpdate) {
        setUpdateBannerDismissed(false);
        if (manual) {
          Alert.alert(
            `Update Available (v${info.latestVersion})`,
            info.releaseNotes || 'A new version of AnaBook is available.',
            [
              { text: 'Later', style: 'cancel' },
              { text: 'Update Now', onPress: () => void Linking.openURL(info.downloadUrl) },
            ]
          );
        }
      } else if (manual) {
        if (info.error) {
          Alert.alert('Update Check Failed', info.error);
        } else {
          Alert.alert('Up to Date', `You are running the latest version (v${info.currentVersion}).`);
        }
      }
    } finally {
      setCheckingUpdate(false);
    }
  }, []);

  useEffect(() => {
    if (!booting) {
      void handleCheckUpdate(false);
    }
  }, [booting, handleCheckUpdate]);

  const handleManualSync = useCallback(async () => {
    setSyncingCatalog(true);
    try {
      const fresh = await syncRemoteCatalog();
      setBooks(fresh.books);
      setCatalogMeta(fresh.meta);
      Alert.alert(
        'Catalog Synced',
        `${fresh.books.length.toLocaleString()} books cached for offline browsing.`
      );
    } catch (err) {
      Alert.alert('Sync Failed', err instanceof Error ? err.message : 'Check your internet connection.');
    } finally {
      setSyncingCatalog(false);
    }
  }, []);

  const handleClearCache = useCallback(async () => {
    const res = await clearCatalogCache();
    setBooks(res.books);
    setCatalogMeta(res.meta);
    Alert.alert('Cache Reset', 'Reverted to bundled starter pack until next sync.');
  }, []);

  const handleChangeThemeMode = useCallback(
    (nextMode: ThemeMode) => {
      persist((prev) => ({ ...prev, themeMode: nextMode }));
    },
    [persist]
  );

  const handleChangeThemePreset = useCallback(
    (nextPreset: ThemePresetKey) => {
      persist((prev) => ({ ...prev, themePreset: nextPreset }));
    },
    [persist]
  );

  const handleChangeFontScale = useCallback(
    (nextScale: FontScaleKey) => {
      persist((prev) => ({ ...prev, fontScale: nextScale }));
    },
    [persist]
  );

  const handleOpenDetail = useCallback((b: Book) => setDetailBook(b), []);

  const handleExplorePath = useCallback(
    (path: string[]) => {
      setExplorePath(path);
      navigateToTab('explore');
    },
    [navigateToTab]
  );

  const handleBrowseLibrary = useCallback(() => navigateToTab('library'), [navigateToTab]);

  const handleClearSubcategory = useCallback(() => {
    setSelectedCategory('');
    setSelectedSubcategory('');
  }, []);

  const handleExploreCategories = useCallback(() => {
    setExplorePath([]);
    navigateToTab('explore');
  }, [navigateToTab]);

  const handleBrowseFiltered = useCallback(
    (cat: string, sub: string) => {
      setSelectedCategory(cat);
      setSelectedSubcategory(sub);
      navigateToTab('library');
    },
    [navigateToTab]
  );

  const handleSelectCategory = useCallback(
    (cat: string) => {
      setExplorePath([cat]);
      navigateToTab('explore');
    },
    [navigateToTab]
  );

  const handleCheckUpdateManual = useCallback(() => {
    void handleCheckUpdate(true);
  }, [handleCheckUpdate]);

  const handleSelectNavTab = useCallback(
    (t: TabKey) => {
      navigateToTab(t, true);
    },
    [navigateToTab]
  );

  const pageWidthStyle = useMemo(() => ({ width: windowWidth, flex: 1 }), [windowWidth]);

  if (booting) {
    return (
      <View style={[styles.splash, { backgroundColor: activeTheme.bg }]}>
        <StatusBar style={themeMode === 'dark' ? 'light' : 'dark'} />
        <Image source={require('./assets/icon.png')} style={styles.splashLogo} />
        <ActivityIndicator color={activeTheme.accent} size="large" />
        <Text style={[styles.splashText, { color: activeTheme.cream }]}>Loading Library…</Text>
      </View>
    );
  }

  return (
    <ThemeProvider
      mode={themeMode}
      preset={themePreset}
      fontScale={fontScale}
      onChangeMode={handleChangeThemeMode}
      onChangePreset={handleChangeThemePreset}
      onChangeFontScale={handleChangeFontScale}
    >
      <SafeAreaView style={[styles.root, { backgroundColor: activeTheme.bg }]} edges={['top']}>
        <StatusBar style={themeMode === 'dark' ? 'light' : 'dark'} />

        {updateInfo?.hasUpdate && !updateBannerDismissed ? (
          <View
            style={[
              styles.updateBanner,
              { backgroundColor: activeTheme.surface, borderColor: activeTheme.accent },
            ]}
          >
            <View style={styles.updateBannerInfo}>
              <Text style={[styles.updateBannerTitle, { color: activeTheme.ink }]} numberOfLines={1}>
                Update Available (v{updateInfo.latestVersion})
              </Text>
              {updateInfo.releaseNotes ? (
                <Text style={[styles.updateBannerSub, { color: activeTheme.muted }]} numberOfLines={1}>
                  {updateInfo.releaseNotes}
                </Text>
              ) : null}
            </View>
            <TouchableOpacity
              style={[styles.updateBannerBtn, { backgroundColor: activeTheme.accent }]}
              onPress={() => void Linking.openURL(updateInfo.downloadUrl)}
              activeOpacity={0.86}
            >
              <Text style={[styles.updateBannerBtnText, { color: activeTheme.creamInk }]}>
                Update Now
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.updateBannerClose}
              onPress={() => setUpdateBannerDismissed(true)}
              accessibilityLabel="Dismiss update notice"
            >
              <CloseIcon size={15} color={activeTheme.muted} />
            </TouchableOpacity>
          </View>
        ) : null}

        <ScrollView
          ref={pagerRef}
          style={styles.stage}
          horizontal
          pagingEnabled
          scrollEnabled={!pagerLocked}
          nestedScrollEnabled
          directionalLockEnabled
          showsHorizontalScrollIndicator={false}
          bounces={false}
          keyboardShouldPersistTaps="handled"
          scrollEventThrottle={16}
          onMomentumScrollEnd={handlePagerMomentumEnd}
        >
          <View style={pageWidthStyle}>
            <HomeScreen
              books={books}
              currentlyReading={currentlyReading}
              progressById={appState.progressById}
              offlineById={appState.offlineById}
              savedIds={appState.savedIds}
              streak={appState.streak}
              downloadingMap={downloadingMap}
              onContinueReading={handleQuickRead}
              onOpenBookDetail={handleOpenDetail}
              onMakeOffline={handleMakeOffline}
              onExplorePath={handleExplorePath}
              onBrowseLibrary={handleBrowseLibrary}
              onRemoveFromReading={handleRemoveFromReading}
              onHorizontalTouchLock={handleHorizontalTouchLock}
            />
          </View>

          <View style={pageWidthStyle}>
            {visitedTabs.includes('library') ? (
              <LibraryScreen
                books={books}
                categories={catalogMeta.cats}
                currentlyReading={currentlyReading}
                progressById={appState.progressById}
                savedIds={appState.savedIds}
                offlineById={appState.offlineById}
                downloadingMap={downloadingMap}
                initialCategory={selectedCategory}
                initialSubcategory={selectedSubcategory}
                onClearSubcategory={handleClearSubcategory}
                onOpenDetail={handleOpenDetail}
                onQuickRead={handleQuickRead}
                onMakeOffline={handleMakeOffline}
                onToggleSave={handleToggleSave}
                onRemoveOffline={handleRemoveOffline}
                onRemoveFromReading={handleRemoveFromReading}
                onExploreCategories={handleExploreCategories}
                onOpenCategoryPath={handleExplorePath}
              />
            ) : null}
          </View>

          <View style={pageWidthStyle}>
            {visitedTabs.includes('explore') ? (
              <ExploreScreen
                books={books}
                categories={catalogMeta.cats}
                offlineById={appState.offlineById}
                downloadingMap={downloadingMap}
                path={explorePath}
                onChangePath={setExplorePath}
                batchDownload={batchDownload}
                onOpenDetail={handleOpenDetail}
                onQuickRead={handleQuickRead}
                onMakeOffline={handleMakeOffline}
                onDownloadFolderOffline={handleDownloadFolderOffline}
                onCancelBatchDownload={handleCancelBatchDownload}
                onBrowseFiltered={handleBrowseFiltered}
                onHorizontalTouchLock={handleHorizontalTouchLock}
              />
            ) : null}
          </View>

          <View style={pageWidthStyle}>
            {visitedTabs.includes('search') ? (
              <SearchScreen
                books={books}
                categories={catalogMeta.cats}
                offlineById={appState.offlineById}
                downloadingMap={downloadingMap}
                savedIds={appState.savedIds}
                onOpenDetail={handleOpenDetail}
                onQuickRead={handleQuickRead}
                onMakeOffline={handleMakeOffline}
                onToggleSave={handleToggleSave}
                onSelectPath={handleExplorePath}
                onHorizontalTouchLock={handleHorizontalTouchLock}
              />
            ) : null}
          </View>

          <View style={pageWidthStyle}>
            {visitedTabs.includes('more') ? (
              <MoreScreen
                books={books}
                catalogMeta={catalogMeta}
                syncingCatalog={syncingCatalog}
                offlineById={appState.offlineById}
                progressById={appState.progressById}
                savedIds={appState.savedIds}
                streak={appState.streak}
                updateInfo={updateInfo}
                checkingUpdate={checkingUpdate}
                onSyncCatalog={handleManualSync}
                onClearCatalogCache={handleClearCache}
                onCheckUpdate={handleCheckUpdateManual}
                onSelectCategory={handleSelectCategory}
                onOpenBookDetail={handleOpenDetail}
                onHorizontalTouchLock={handleHorizontalTouchLock}
              />
            ) : null}
          </View>
        </ScrollView>

        <BottomNavBar
          activeTab={activeTab}
          onSelectTab={handleSelectNavTab}
          bottomInset={insets.bottom}
        />

        <BookDetailModal
          book={detailBook}
          progress={detailBook ? appState.progressById[detailBook.id] : undefined}
          offlineEntry={detailBook ? appState.offlineById[detailBook.id] : undefined}
          isCurrentRead={Boolean(detailBook && currentlyReading?.id === detailBook.id)}
          isSaved={Boolean(detailBook && appState.savedIds.includes(detailBook.id))}
          downloadingPct={detailBook ? downloadingMap[detailBook.id] ?? null : null}
          onClose={() => setDetailBook(null)}
          onReadOnline={handleReadOnline}
          onOpenOffline={handleOpenOffline}
          onMakeOffline={handleMakeOffline}
          onRemoveOffline={handleRemoveOffline}
          onToggleSave={handleToggleSave}
          onSetCurrentlyReading={handleSetCurrentlyReading}
          onUpdateProgress={handleUpdateProgress}
        />

        <ReaderModal
          book={readerBook}
          offlineEntry={readerBook ? appState.offlineById[readerBook.id] : undefined}
          downloadingPct={readerBook ? downloadingMap[readerBook.id] ?? null : null}
          onClose={() => setReaderBook(null)}
          onMakeOffline={handleMakeOffline}
          onOpenOfflineExternal={handleOpenOffline}
        />
      </SafeAreaView>
    </ThemeProvider>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <MainApp />
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  stage: { flex: 1 },
  splash: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 14,
  },
  splashLogo: {
    width: 88,
    height: 88,
    borderRadius: 22,
  },
  splashText: {
    fontSize: 15,
    fontWeight: '600',
  },
  updateBanner: {
    marginHorizontal: 14,
    marginTop: 6,
    borderRadius: 14,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 9,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  updateBannerInfo: { flex: 1, gap: 1 },
  updateBannerTitle: { fontSize: 12.5, fontWeight: '800' },
  updateBannerSub: { fontSize: 11 },
  updateBannerBtn: {
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  updateBannerBtnText: { fontSize: 11.5, fontWeight: '800' },
  updateBannerClose: { padding: 4 },
});
