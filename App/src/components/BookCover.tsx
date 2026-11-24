import React, { useEffect, useMemo, useState } from 'react';
import { Image, StyleSheet, Text, View } from 'react-native';

import { useAppTheme } from '../context/ThemeContext';
import { getThumbnailUrl } from '../services/libraryStore';
import type { Book } from '../types';

const CLOTH_PALETTES = [
  '#2B1B17',
  '#172B24',
  '#182338',
  '#2E1A2C',
  '#2E2314',
  '#142A30',
  '#331922',
];

function pickClothBg(book: Book): string {
  const seed = `${book.title || ''}|${book.cat || ''}`;
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = ((hash * 31) + seed.charCodeAt(i)) >>> 0;
  }
  return CLOTH_PALETTES[hash % CLOTH_PALETTES.length];
}

interface Props {
  book: Book;
  localCoverUri?: string;
  width: number;
  height: number;
  borderRadius?: number;
  isOffline?: boolean;
}

export function BookCover({
  book,
  localCoverUri,
  width,
  height,
  borderRadius = 10,
  isOffline = false,
}: Props) {
  const { theme } = useAppTheme();
  const [stage, setStage] = useState<'local' | 'primary' | 'fallback' | 'none'>(
    localCoverUri ? 'local' : getThumbnailUrl(book, false) ? 'primary' : 'none'
  );

  useEffect(() => {
    setStage(localCoverUri ? 'local' : getThumbnailUrl(book, false) ? 'primary' : 'none');
  }, [book.id, book.coverId, localCoverUri]);

  const uri =
    stage === 'local'
      ? localCoverUri
      : stage === 'primary'
      ? getThumbnailUrl(book, false)
      : stage === 'fallback'
      ? getThumbnailUrl(book, true)
      : '';

  const leafCat = (book.sub || book.cat).split('/').pop() || book.cat;
  const leftRadius = Math.max(2, Math.round(borderRadius * 0.35));
  const cornerRadii = {
    borderTopLeftRadius: leftRadius,
    borderBottomLeftRadius: leftRadius,
    borderTopRightRadius: borderRadius,
    borderBottomRightRadius: borderRadius,
  };
  const clothBg = useMemo(() => pickClothBg(book), [book.title, book.cat]);

  return (
    <View style={[styles.shadowShell, { width, height }, cornerRadii]}>
      <View
        style={[
          styles.wrap,
          cornerRadii,
          {
            backgroundColor: uri ? theme.surfaceAlt : clothBg,
            borderColor: uri ? theme.border : 'rgba(255, 255, 255, 0.14)',
          },
        ]}
      >
        {uri ? (
          <Image
            source={{ uri }}
            style={styles.img}
            resizeMode="cover"
            onError={() => {
              if (stage === 'local') {
                setStage(getThumbnailUrl(book, false) ? 'primary' : 'none');
              } else if (stage === 'primary') {
                setStage(getThumbnailUrl(book, true) ? 'fallback' : 'none');
              } else {
                setStage('none');
              }
            }}
          />
        ) : (
          <View style={[styles.fallbackOuter, { backgroundColor: clothBg }]}>
            <View
              style={[
                styles.fallbackFrame,
                {
                  borderTopLeftRadius: Math.max(1, leftRadius - 2),
                  borderBottomLeftRadius: Math.max(1, leftRadius - 2),
                  borderTopRightRadius: Math.max(2, borderRadius - 3),
                  borderBottomRightRadius: Math.max(2, borderRadius - 3),
                },
              ]}
            >
              <Text numberOfLines={1} style={styles.fbCat}>
                {leafCat.toUpperCase()}
              </Text>
              <Text numberOfLines={4} style={styles.fbTitle}>
                {book.title}
              </Text>
              <Text numberOfLines={1} style={styles.fbAuthor}>
                {book.author}
              </Text>
            </View>
          </View>
        )}

        {/* Realistic left-edge spine shading & highlight crease */}
        <View style={styles.spineShade} pointerEvents="none" />
        <View style={styles.spineHighlight} pointerEvents="none" />

        {isOffline ? (
          <View style={[styles.offlineBadge, { backgroundColor: theme.sage }]}>
            <Text style={styles.offlineBadgeText}>OFFLINE</Text>
          </View>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  shadowShell: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 5 },
    shadowOpacity: 0.24,
    shadowRadius: 8,
    elevation: 5,
  },
  wrap: {
    flex: 1,
    borderWidth: 1,
    overflow: 'hidden',
    position: 'relative',
  },
  img: {
    width: '100%',
    height: '100%',
  },
  fallbackOuter: {
    flex: 1,
    paddingVertical: 5,
    paddingRight: 5,
    paddingLeft: 10,
  },
  fallbackFrame: {
    flex: 1,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.16)',
    paddingHorizontal: 6,
    paddingVertical: 6,
    justifyContent: 'space-between',
  },
  fbCat: {
    color: '#E5C29F',
    fontSize: 7.5,
    fontWeight: '800',
    letterSpacing: 0.7,
  },
  fbTitle: {
    color: '#F7F3EE',
    fontSize: 10.5,
    fontWeight: '700',
    lineHeight: 13.5,
  },
  fbAuthor: {
    color: 'rgba(247, 243, 238, 0.72)',
    fontSize: 8.5,
    fontWeight: '600',
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: 'rgba(255, 255, 255, 0.16)',
    paddingTop: 4,
  },
  spineShade: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    width: 6,
    backgroundColor: 'rgba(0, 0, 0, 0.22)',
  },
  spineHighlight: {
    position: 'absolute',
    left: 6,
    top: 0,
    bottom: 0,
    width: 1.5,
    backgroundColor: 'rgba(255, 255, 255, 0.22)',
  },
  offlineBadge: {
    position: 'absolute',
    top: 5,
    right: 5,
    paddingHorizontal: 5,
    paddingVertical: 2,
    borderRadius: 4,
  },
  offlineBadgeText: {
    color: '#F7F3EE',
    fontSize: 7.5,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
});
