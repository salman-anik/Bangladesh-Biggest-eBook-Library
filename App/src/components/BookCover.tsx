import React, { useEffect, useState } from 'react';
import { Image, StyleSheet, Text, View } from 'react-native';

import { useAppTheme } from '../context/ThemeContext';
import { getThumbnailUrl } from '../services/libraryStore';
import type { Book } from '../types';

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

  return (
    <View
      style={[
        styles.wrap,
        {
          width,
          height,
          borderRadius,
          backgroundColor: theme.surfaceAlt,
          borderColor: theme.border,
        },
      ]}
    >
      {uri ? (
        <Image
          source={{ uri }}
          style={[styles.img, { borderRadius }]}
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
        <View style={[styles.fallback, { borderRadius, backgroundColor: theme.surface }]}>
          <Text numberOfLines={1} style={[styles.fbCat, { color: theme.accent }]}>
            {leafCat.toUpperCase()}
          </Text>
          <Text numberOfLines={4} style={[styles.fbTitle, { color: theme.ink }]}>
            {book.title}
          </Text>
          <Text numberOfLines={1} style={[styles.fbAuthor, { color: theme.muted, borderTopColor: theme.border }]}>
            {book.author}
          </Text>
        </View>
      )}

      {isOffline ? (
        <View style={[styles.offlineBadge, { backgroundColor: theme.sage }]}>
          <Text style={styles.offlineBadgeText}>OFFLINE</Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderWidth: 1,
    overflow: 'hidden',
    position: 'relative',
  },
  img: {
    width: '100%',
    height: '100%',
  },
  fallback: {
    flex: 1,
    padding: 8,
    justifyContent: 'space-between',
  },
  fbCat: {
    fontSize: 8,
    fontWeight: '700',
    letterSpacing: 0.6,
  },
  fbTitle: {
    fontSize: 11,
    fontWeight: '700',
    lineHeight: 14,
  },
  fbAuthor: {
    fontSize: 9,
    borderTopWidth: StyleSheet.hairlineWidth,
    paddingTop: 4,
  },
  offlineBadge: {
    position: 'absolute',
    bottom: 5,
    left: 5,
    paddingHorizontal: 5,
    paddingVertical: 2,
    borderRadius: 4,
  },
  offlineBadgeText: {
    color: '#F7F3EE',
    fontSize: 8,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
});
