import React, { useEffect, useMemo, useState } from 'react';
import { Image, StyleSheet, Text, View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';

import { useAppTheme } from '../context/ThemeContext';

// eslint-disable-next-line @typescript-eslint/no-var-requires
const AUTHOR_PHOTOS: Record<string, string> = require('../../assets/author_photos.json');

interface ArchivalPalette {
  bg: string;
  ring: string;
  text: string;
}

const ARCHIVAL_PALETTES: ArchivalPalette[] = [
  { bg: '#3E2723', ring: '#C6927A', text: '#F7E7DC' }, // Deep espresso bronze
  { bg: '#1F3A30', ring: '#86B8A3', text: '#E7F5EF' }, // Forest sage
  { bg: '#1E2942', ring: '#88A9E6', text: '#EBF1FC' }, // Midnight indigo
  { bg: '#4A1F2B', ring: '#D98A9C', text: '#FCEEF2' }, // Burgundy cloth
  { bg: '#5A2D21', ring: '#E59D85', text: '#FCEEE9' }, // Warm terracotta
  { bg: '#19353C', ring: '#7BC4D4', text: '#E7F6F8' }, // Slate teal
];

const HONORIFIC_PREFIXES = new Set([
  'ড.',
  'ড',
  'অধ্যাপক',
  'মাওলানা',
  'আল্লামা',
  'মুফতি',
  'dr.',
  'dr',
  'prof.',
  'prof',
  'md.',
  'md',
  'mr.',
  'mr',
  'mrs.',
  'mrs',
  'ms.',
  'ms',
]);

export function normalizeAuthorKey(name: string): string {
  return (name || '').trim().toLowerCase();
}

export function getAuthorPhotoId(name: string): string | null {
  const key = normalizeAuthorKey(name);
  if (!key) return null;
  if (AUTHOR_PHOTOS[key]) return AUTHOR_PHOTOS[key];
  const firstSegment = key.split(/[,&|/]/)[0].trim();
  if (firstSegment && AUTHOR_PHOTOS[firstSegment]) return AUTHOR_PHOTOS[firstSegment];
  return null;
}

function getDriveAvatarUrl(id: string, fallback = false): string {
  if (id.startsWith('http://') || id.startsWith('https://')) {
    return id;
  }
  return fallback
    ? `https://lh3.googleusercontent.com/d/${encodeURIComponent(id)}=w240`
    : `https://drive.google.com/thumbnail?id=${encodeURIComponent(id)}&sz=w240`;
}

function pickPaletteIndex(name: string): number {
  const s = name || 'author';
  let hash = 0;
  for (let i = 0; i < s.length; i++) {
    hash = (hash * 31 + s.charCodeAt(i)) >>> 0;
  }
  return hash % ARCHIVAL_PALETTES.length;
}

export function getAuthorInitials(name: string): string {
  const cleaned = (name || '').replace(/\(.*?\)/g, ' ').trim();
  const rawWords = cleaned.split(/\s+/).filter(Boolean);
  const words = rawWords.filter((w) => !HONORIFIC_PREFIXES.has(w.toLowerCase()));
  const target = words.length > 0 ? words : rawWords;
  if (target.length === 0) return '?';

  const chars = target
    .slice(0, 2)
    .map((w) => {
      const ch = Array.from(w)[0] || '';
      return /[a-z]/i.test(ch) ? ch.toUpperCase() : ch;
    })
    .filter(Boolean);

  return chars.join('') || '?';
}

function LiteraryMonogramAvatar({ name, size }: { name: string; size: number }) {
  const palette = useMemo(() => ARCHIVAL_PALETTES[pickPaletteIndex(name)], [name]);
  const initials = useMemo(() => getAuthorInitials(name), [name]);
  const fontSize = Math.max(12, Math.round(size * (initials.length > 1 ? 0.34 : 0.4)));

  return (
    <View style={[styles.monogramWrap, { width: size, height: size, backgroundColor: palette.bg }]}>
      <Svg width={size} height={size} viewBox="0 0 80 80" style={styles.monogramSvg}>
        <Circle cx="40" cy="40" r="35" fill="none" stroke={palette.ring} strokeWidth={1.6} opacity={0.55} />
        <Circle cx="40" cy="40" r="29" fill={palette.ring} opacity={0.12} />
      </Svg>
      <Text
        style={[
          styles.monogramText,
          {
            color: palette.text,
            fontSize,
          },
        ]}
        numberOfLines={1}
      >
        {initials}
      </Text>
    </View>
  );
}

interface Props {
  name: string;
  size?: number;
}

export const AuthorAvatar = React.memo(function AuthorAvatar({ name, size = 40 }: Props) {
  const { theme } = useAppTheme();
  const photoId = getAuthorPhotoId(name);
  const [stage, setStage] = useState<'primary' | 'fallback' | 'avatar'>(photoId ? 'primary' : 'avatar');

  useEffect(() => {
    setStage(photoId ? 'primary' : 'avatar');
  }, [name, photoId]);

  const radius = size / 2;
  const uri =
    photoId && stage === 'primary'
      ? getDriveAvatarUrl(photoId, false)
      : photoId && stage === 'fallback'
      ? getDriveAvatarUrl(photoId, true)
      : '';

  return (
    <View
      style={[
        styles.wrap,
        {
          width: size,
          height: size,
          borderRadius: radius,
          borderColor: theme.border,
          backgroundColor: theme.surfaceAlt,
        },
      ]}
    >
      <LiteraryMonogramAvatar name={name} size={size} />

      {uri ? (
        <Image
          source={{ uri }}
          style={[
            styles.photo,
            {
              width: size,
              height: size,
              borderRadius: radius,
            },
          ]}
          resizeMode="cover"
          onError={() => {
            if (stage === 'primary' && !(photoId || '').startsWith('http')) {
              setStage('fallback');
            } else {
              setStage('avatar');
            }
          }}
        />
      ) : null}
    </View>
  );
});

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
    borderWidth: 1.5,
  },
  monogramWrap: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  monogramSvg: {
    position: 'absolute',
    top: 0,
    left: 0,
  },
  monogramText: {
    fontWeight: '800',
    letterSpacing: 0.6,
    textAlign: 'center',
  },
  photo: {
    position: 'absolute',
    top: 0,
    left: 0,
  },
});
