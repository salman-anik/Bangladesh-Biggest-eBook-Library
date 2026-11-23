import { StatusBar } from 'expo-status-bar';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Alert, BackHandler, StyleSheet, Text, View } from 'react-native';
import { SafeAreaProvider, SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';

import { BookDetailModal } from './src/components/BookDetailModal';
import { BottomNavBar } from './src/components/BottomNavBar';
import { ReaderModal } from './src/components/ReaderModal';
import { ThemeProvider } from './src/context/ThemeContext';
import { ExploreScreen } from './src/screens/ExploreScreen';
import { HomeScreen } from './src/screens/HomeScreen';
import { LibraryScreen } from './src/screens/LibraryScreen';
import { MoreScreen } from './src/screens/MoreScreen';
import { StatsScreen } from './src/screens/StatsScreen';
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

function MainApp() {
  const insets = useSafeAreaInsets();
  const [activeTab, setActiveTab] = useState<TabKey>('home');
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
        setActiveTab('home');
        return true;
      }
      return false;
    });
    return () => sub.remove();
  }, [readerBook, detailBook, activeTab, explorePath.length]);

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
    if (!books.length) return null;
    if (appState.currentlyReadingId) {
      const found = books.find((b) => b.id === appState.currentlyReadingId);
      if (found) return found;
    }
    return books.find((b) => Boolean(b.coverId)) || books[0];
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

  if (booting) {
    return (
      <View style={[styles.splash, { backgroundColor: activeTheme.bg }]}>
        <StatusBar style={themeMode === 'dark' ? 'light' : 'dark'} />
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

        <View style={styles.stage}>
          {activeTab === 'home' ? (
            <HomeScreen
              books={books}
              currentlyReading={currentlyReading}
              progressById={appState.progressById}
              offlineById={appState.offlineById}
              savedIds={appState.savedIds}
              streak={appState.streak}
              downloadingMap={downloadingMap}
              onContinueReading={handleQuickRead}
              onOpenBookDetail={(b) => setDetailBook(b)}
              onMakeOffline={handleMakeOffline}
              onExplorePath={(path) => {
                setExplorePath(path);
                setActiveTab('explore');
              }}
              onBrowseLibrary={() => setActiveTab('library')}
            />
          ) : activeTab === 'library' ? (
            <LibraryScreen
              books={books}
              categories={catalogMeta.cats}
              offlineById={appState.offlineById}
              downloadingMap={downloadingMap}
              initialCategory={selectedCategory}
              initialSubcategory={selectedSubcategory}
              onClearSubcategory={() => setSelectedSubcategory('')}
              onOpenDetail={(b) => setDetailBook(b)}
              onQuickRead={handleQuickRead}
              onMakeOffline={handleMakeOffline}
            />
          ) : activeTab === 'explore' ? (
            <ExploreScreen
              books={books}
              categories={catalogMeta.cats}
              offlineById={appState.offlineById}
              downloadingMap={downloadingMap}
              path={explorePath}
              onChangePath={setExplorePath}
              batchDownload={batchDownload}
              onOpenDetail={(b) => setDetailBook(b)}
              onQuickRead={handleQuickRead}
              onMakeOffline={handleMakeOffline}
              onDownloadFolderOffline={handleDownloadFolderOffline}
              onCancelBatchDownload={handleCancelBatchDownload}
              onBrowseFiltered={(cat, sub) => {
                setSelectedCategory(cat);
                setSelectedSubcategory(sub);
                setActiveTab('library');
              }}
            />
          ) : activeTab === 'stats' ? (
            <StatsScreen
              books={books}
              progressById={appState.progressById}
              savedIds={appState.savedIds}
              offlineById={appState.offlineById}
              streak={appState.streak}
              onSelectCategory={(cat) => {
                setExplorePath([cat]);
                setActiveTab('explore');
              }}
              onOpenBookDetail={(b) => setDetailBook(b)}
            />
          ) : (
            <MoreScreen
              books={books}
              catalogMeta={catalogMeta}
              syncingCatalog={syncingCatalog}
              offlineById={appState.offlineById}
              onSyncCatalog={handleManualSync}
              onClearCatalogCache={handleClearCache}
              onOpenOfflineBook={(entry) => {
                const b = books.find((x) => x.id === entry.bookId) || {
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
                void handleOpenOffline(b, entry);
              }}
              onRemoveOfflineBook={handleRemoveOffline}
            />
          )}
        </View>

        <BottomNavBar
          activeTab={activeTab}
          onSelectTab={(t) => {
            if (t === 'explore' && activeTab !== 'explore') {
              setExplorePath([]);
            }
            setActiveTab(t);
          }}
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
    gap: 12,
  },
  splashText: {
    fontSize: 15,
    fontWeight: '600',
  },
});
