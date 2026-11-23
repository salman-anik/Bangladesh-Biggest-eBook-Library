import * as FileSystem from 'expo-file-system/legacy';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Image,
  Modal,
  PanResponder,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { WebView, type WebViewMessageEvent } from 'react-native-webview';

import { useAppTheme } from '../context/ThemeContext';
import type { Book, OfflineBookEntry } from '../types';
import {
  BookOpenIcon,
  CloseIcon,
  DownloadIcon,
  LockIcon,
  UnlockIcon,
} from './Icons';

interface Props {
  book: Book | null;
  offlineEntry?: OfflineBookEntry;
  downloadingPct: number | null;
  onClose: () => void;
  onMakeOffline: (book: Book) => void;
  onOpenOfflineExternal: (book: Book, entry: OfflineBookEntry) => void;
}

export function ReaderModal({
  book,
  offlineEntry,
  downloadingPct,
  onClose,
  onMakeOffline,
  onOpenOfflineExternal,
}: Props) {
  const { theme, fs } = useAppTheme();
  const [offlineText, setOfflineText] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [locked, setLocked] = useState(false);
  const [scrollPct, setScrollPct] = useState(0);
  const [scrubbing, setScrubbing] = useState(false);

  const webViewRef = useRef<any>(null);
  const textScrollRef = useRef<React.ComponentRef<typeof ScrollView>>(null);
  const railHeightRef = useRef(360);
  const textContentHeightRef = useRef(1);
  const textViewHeightRef = useRef(1);

  const isImage = book ? ['JPG', 'JPEG', 'PNG'].includes(book.fmt.toUpperCase()) : false;
  const isText = book ? ['TXT', 'MD'].includes(book.fmt.toUpperCase()) : false;

  useEffect(() => {
    setOfflineText(null);
    setLoading(true);
    setLocked(false);
    setScrollPct(0);
    if (book && offlineEntry && isText) {
      FileSystem.readAsStringAsync(offlineEntry.localUri)
        .then((txt) => {
          setOfflineText(txt);
          setLoading(false);
        })
        .catch(() => {
          setOfflineText('Unable to read local text file.');
          setLoading(false);
        });
    }
  }, [book?.id, offlineEntry?.localUri, isText]);

  // Inject mistouch guard whenever lock toggles inside WebView
  useEffect(() => {
    if (!book || (offlineEntry && (isImage || isText))) return;
    const js = locked
      ? `(function(){
          window.__bdLock=true;
          document.documentElement.style.userSelect='none';
          document.documentElement.style.webkitUserSelect='none';
          if(!window.__bdGuardAttached){
            window.__bdGuardAttached=true;
            document.addEventListener('click',function(e){if(window.__bdLock){e.preventDefault();e.stopPropagation();}},true);
          }
        })();true;`
      : `(function(){
          window.__bdLock=false;
          document.documentElement.style.userSelect='auto';
          document.documentElement.style.webkitUserSelect='auto';
        })();true;`;
    webViewRef.current?.injectJavaScript(js);
  }, [locked, book?.id, offlineEntry, isImage, isText]);

  const applyScrollRatio = (ratio: number) => {
    const clamped = Math.max(0, Math.min(1, ratio));
    setScrollPct(clamped);
    if (offlineEntry && isText) {
      const maxOffset = Math.max(0, textContentHeightRef.current - textViewHeightRef.current);
      textScrollRef.current?.scrollTo({ y: clamped * maxOffset, animated: false });
    } else if (!isImage) {
      const js = `(function(){
        var r=${clamped};
        var docH=Math.max(document.documentElement.scrollHeight||0, document.body.scrollHeight||0) - window.innerHeight;
        if(docH>20){ window.scrollTo(0, r*docH); return; }
        var els=document.querySelectorAll('*');
        for(var i=0;i<els.length;i++){
          var el=els[i];
          if(el.scrollHeight - el.clientHeight > 80){
            el.scrollTop = r * (el.scrollHeight - el.clientHeight);
          }
        }
      })();true;`;
      webViewRef.current?.injectJavaScript(js);
    }
  };

  const panResponder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => true,
        onMoveShouldSetPanResponder: () => true,
        onPanResponderGrant: (evt) => {
          setScrubbing(true);
          const y = evt.nativeEvent.locationY;
          applyScrollRatio(y / Math.max(80, railHeightRef.current));
        },
        onPanResponderMove: (evt) => {
          const y = evt.nativeEvent.locationY;
          applyScrollRatio(y / Math.max(80, railHeightRef.current));
        },
        onPanResponderRelease: () => setScrubbing(false),
        onPanResponderTerminate: () => setScrubbing(false),
      }),
    [offlineEntry, isImage, isText]
  );

  if (!book) return null;

  const previewUrl = `https://drive.google.com/file/d/${encodeURIComponent(book.id)}/preview`;

  const injectedScrollAndLock = `
    (function(){
      window.__bdLock = ${locked ? 'true' : 'false'};
      if(!window.__bdGuardAttached){
        window.__bdGuardAttached=true;
        document.addEventListener('click',function(e){if(window.__bdLock){e.preventDefault();e.stopPropagation();}},true);
      }
      window.addEventListener('scroll',function(){
        var docH=Math.max(document.documentElement.scrollHeight||0, document.body.scrollHeight||0)-window.innerHeight;
        if(docH>0 && window.ReactNativeWebView){
          window.ReactNativeWebView.postMessage(JSON.stringify({pct: window.scrollY/docH}));
        }
      },{passive:true});
    })();true;
  `;

  const showScrollRail = !isImage;
  const trackH = Math.max(80, railHeightRef.current - 36);
  const thumbTop = Math.round(scrollPct * trackH);

  return (
    <Modal
      visible={Boolean(book)}
      animationType="slide"
      onRequestClose={() => {
        if (locked) setLocked(false);
        else onClose();
      }}
    >
      <SafeAreaView style={[styles.root, { backgroundColor: theme.bg }]} edges={locked ? [] : ['top']}>
        {/* Header Bar (hidden during locked full-screen reading) */}
        {!locked ? (
          <View style={[styles.header, { backgroundColor: theme.surfaceDeep, borderBottomColor: theme.border }]}>
            <TouchableOpacity
              style={[styles.iconBtn, { backgroundColor: theme.surface, borderColor: theme.border }]}
              onPress={onClose}
              accessibilityLabel="Close reader"
            >
              <CloseIcon size={17} color={theme.ink} />
            </TouchableOpacity>

            <View style={styles.titleWrap}>
              <Text style={[styles.title, { color: theme.ink, fontSize: fs(13.5) }]} numberOfLines={1}>
                {book.title}
              </Text>
            </View>

            <TouchableOpacity
              style={[styles.iconBtn, { backgroundColor: theme.surface, borderColor: theme.accent }]}
              onPress={() => setLocked(true)}
              accessibilityLabel="Lock full-screen reader"
            >
              <LockIcon size={16} color={theme.accent} />
            </TouchableOpacity>

            {offlineEntry ? (
              <TouchableOpacity
                style={[styles.iconBtn, { backgroundColor: theme.cream, borderColor: theme.cream }]}
                onPress={() => onOpenOfflineExternal(book, offlineEntry)}
                accessibilityLabel="Open offline file"
              >
                <BookOpenIcon size={16} color={theme.creamInk} />
              </TouchableOpacity>
            ) : downloadingPct !== null ? (
              <View style={[styles.iconBtn, { backgroundColor: theme.surface, borderColor: theme.accent }]}>
                <Text style={[styles.pctMini, { color: theme.accent }]}>{downloadingPct}%</Text>
              </View>
            ) : (
              <TouchableOpacity
                style={[styles.iconBtn, { backgroundColor: theme.accent, borderColor: theme.accent }]}
                onPress={() => onMakeOffline(book)}
                accessibilityLabel="Save offline"
              >
                <DownloadIcon size={16} color={theme.creamInk} />
              </TouchableOpacity>
            )}
          </View>
        ) : null}

        {/* Reader Canvas */}
        <View style={styles.body}>
          {offlineEntry && isImage ? (
            <Image
              source={{ uri: offlineEntry.localUri }}
              style={styles.fullImage}
              resizeMode="contain"
              onLoadEnd={() => setLoading(false)}
            />
          ) : offlineEntry && isText && offlineText !== null ? (
            <ScrollView
              ref={textScrollRef}
              contentContainerStyle={styles.textReaderPad}
              scrollEventThrottle={32}
              onLayout={(e) => {
                textViewHeightRef.current = e.nativeEvent.layout.height;
              }}
              onContentSizeChange={(_w, h) => {
                textContentHeightRef.current = h;
              }}
              onScroll={(e) => {
                if (scrubbing) return;
                const maxO = Math.max(1, e.nativeEvent.contentSize.height - e.nativeEvent.layoutMeasurement.height);
                setScrollPct(Math.max(0, Math.min(1, e.nativeEvent.contentOffset.y / maxO)));
              }}
            >
              <Text style={[styles.textReaderBody, { color: theme.ink, fontSize: fs(15) }]} selectable={!locked}>
                {offlineText}
              </Text>
            </ScrollView>
          ) : (
            <>
              <WebView
                ref={(el: unknown) => {
                  webViewRef.current = el;
                }}
                source={{ uri: previewUrl }}
                style={styles.webview}
                onLoadEnd={(): void => setLoading(false)}
                injectedJavaScript={injectedScrollAndLock}
                onMessage={(ev: WebViewMessageEvent): void => {
                  try {
                    const p = JSON.parse(ev.nativeEvent.data);
                    if (typeof p.pct === 'number' && !scrubbing) {
                      setScrollPct(Math.max(0, Math.min(1, p.pct)));
                    }
                  } catch {
                    // Ignore malformed message
                  }
                }}
                javaScriptEnabled
                domStorageEnabled
              />
              {loading ? (
                <View style={[styles.spinnerOverlay, { backgroundColor: theme.bg }]} pointerEvents="none">
                  <ActivityIndicator size="large" color={theme.accent} />
                </View>
              ) : null}
            </>
          )}

          {/* Right-Side Fast Scrollbar Rail (Always active, even when locked!) */}
          {showScrollRail ? (
            <View
              style={styles.railWrap}
              onLayout={(e) => {
                railHeightRef.current = e.nativeEvent.layout.height;
              }}
              {...panResponder.panHandlers}
            >
              <View style={[styles.railTrack, { backgroundColor: theme.surface + 'CC', borderColor: theme.border }]}>
                <View
                  style={[
                    styles.railThumb,
                    {
                      backgroundColor: theme.accent,
                      transform: [{ translateY: thumbTop }],
                    },
                  ]}
                />
              </View>
            </View>
          ) : null}

          {scrubbing ? (
            <View style={[styles.scrubPill, { backgroundColor: theme.surfaceDeep, borderColor: theme.accent }]}>
              <Text style={[styles.scrubText, { color: theme.ink }]}>{Math.round(scrollPct * 100)}%</Text>
            </View>
          ) : null}

          {/* Floating Unlock Button during Full-Screen Locked Reading */}
          {locked ? (
            <TouchableOpacity
              style={[styles.unlockFab, { backgroundColor: theme.surfaceDeep + 'E6', borderColor: theme.accent }]}
              onPress={() => setLocked(false)}
              activeOpacity={0.85}
              accessibilityLabel="Unlock controls"
            >
              <UnlockIcon size={18} color={theme.accent} />
            </TouchableOpacity>
          ) : null}
        </View>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderBottomWidth: 1,
    gap: 8,
  },
  iconBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pctMini: { fontSize: 10, fontWeight: '800' },
  titleWrap: { flex: 1, paddingHorizontal: 4 },
  title: { fontWeight: '700' },
  body: { flex: 1, position: 'relative' },
  webview: { flex: 1, backgroundColor: '#1A1817' },
  fullImage: { flex: 1, width: '100%', height: '100%' },
  textReaderPad: { padding: 18, paddingRight: 36 },
  textReaderBody: { lineHeight: 24 },
  spinnerOverlay: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  railWrap: {
    position: 'absolute',
    top: 48,
    bottom: 24,
    right: 4,
    width: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  railTrack: {
    width: 8,
    height: '100%',
    borderRadius: 4,
    borderWidth: 1,
    overflow: 'hidden',
  },
  railThumb: {
    width: '100%',
    height: 36,
    borderRadius: 4,
  },
  scrubPill: {
    position: 'absolute',
    right: 36,
    top: '48%',
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  scrubText: { fontSize: 12, fontWeight: '800' },
  unlockFab: {
    position: 'absolute',
    top: 38,
    left: 16,
    width: 42,
    height: 42,
    borderRadius: 21,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
