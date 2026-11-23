import React, { useEffect, useMemo, useState } from 'react';
import { Image, StyleSheet, View } from 'react-native';
import Svg, { Circle, Ellipse, Path, Rect } from 'react-native-svg';

import { useAppTheme } from '../context/ThemeContext';

// eslint-disable-next-line @typescript-eslint/no-var-requires
const AUTHOR_PHOTOS: Record<string, string> = require('../../assets/author_photos.json');

interface AvatarStyle {
  bg: string;
  accent: string;
  skin: string;
  hair: string;
  shirt: string;
  hairStyle: 'waves' | 'parted' | 'bob' | 'classic' | 'bun' | 'short';
}

const EDITORIAL_AVATARS: AvatarStyle[] = [
  {
    bg: '#D9A790',
    accent: '#C6927A',
    skin: '#F2D0BA',
    hair: '#2E2320',
    shirt: '#486359',
    hairStyle: 'parted',
  },
  {
    bg: '#9FB5AA',
    accent: '#5F7A6F',
    skin: '#E6BC9E',
    hair: '#1E1A18',
    shirt: '#6E493A',
    hairStyle: 'classic',
  },
  {
    bg: '#DECAB8',
    accent: '#B56E52',
    skin: '#F5DAC6',
    hair: '#3A2823',
    shirt: '#2D2826',
    hairStyle: 'bob',
  },
  {
    bg: '#C7B6C9',
    accent: '#7A637D',
    skin: '#E8C2A6',
    hair: '#251D1B',
    shirt: '#4A5D6E',
    hairStyle: 'bun',
  },
  {
    bg: '#D5BF97',
    accent: '#8D7246',
    skin: '#DFB392',
    hair: '#1D1816',
    shirt: '#5F7A6F',
    hairStyle: 'short',
  },
  {
    bg: '#C99B9A',
    accent: '#7D4A4E',
    skin: '#F0CAB2',
    hair: '#302320',
    shirt: '#3E4B59',
    hairStyle: 'waves',
  },
];

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

function pickAvatarIndex(name: string): number {
  const s = name || 'author';
  let hash = 0;
  for (let i = 0; i < s.length; i++) {
    hash = (hash * 31 + s.charCodeAt(i)) >>> 0;
  }
  return hash % EDITORIAL_AVATARS.length;
}

function PinterestEditorialAvatar({ name, size }: { name: string; size: number }) {
  const art = useMemo(() => EDITORIAL_AVATARS[pickAvatarIndex(name)], [name]);
  return (
    <Svg width={size} height={size} viewBox="0 0 80 80">
      <Rect x="0" y="0" width="80" height="80" fill={art.bg} />
      {/* Subtle Pinterest editorial backdrop circle */}
      <Circle cx="40" cy="36" r="28" fill={art.accent} opacity={0.28} />

      {/* Back hair layer for long / bun styles */}
      {art.hairStyle === 'waves' ? (
        <Path d="M22 36c0-13 8-21 18-21s18 8 18 21v20H22V36z" fill={art.hair} />
      ) : null}
      {art.hairStyle === 'bob' ? (
        <Path d="M23 36c0-12 7.5-20 17-20s17 8 17 20l2 14H21l2-14z" fill={art.hair} />
      ) : null}
      {art.hairStyle === 'bun' ? (
        <>
          <Circle cx="40" cy="14" r="8" fill={art.hair} />
          <Path d="M25 35c0-10 6.8-17 15-17s15 7 15 17H25z" fill={art.hair} />
        </>
      ) : null}

      {/* Shoulders / minimalist garment */}
      <Path d="M14 80c2-15 12-23 26-23s24 8 26 23H14z" fill={art.shirt} />
      {/* Neck */}
      <Rect x="34.5" y="45" width="11" height="14" rx="5.5" fill={art.skin} />
      {/* Minimalist collarbone shadow */}
      <Ellipse cx="40" cy="52" rx="5.5" ry="2.2" fill="#000" opacity={0.08} />
      {/* Face */}
      <Ellipse cx="40" cy="35" rx="13" ry="15.5" fill={art.skin} />

      {/* Minimalist facial suggestion (calm Pinterest line style) */}
      <Path d="M33.5 34.5q1.5-1.4 3 0M43.5 34.5q1.5-1.4 3 0" stroke={art.hair} strokeWidth={1.6} strokeLinecap="round" fill="none" />
      <Path d="M37 42.5q3 1.8 6 0" stroke={art.hair} strokeWidth={1.3} strokeLinecap="round" fill="none" opacity={0.65} />

      {/* Top hair silhouettes */}
      {art.hairStyle === 'parted' ? (
        <Path d="M26.5 33c0-10 6-16.5 14-16.5 7.5 0 13 6 13 15-4-4-9.5-5.5-16-4.5-4.5.7-8.2 3-11 6z" fill={art.hair} />
      ) : art.hairStyle === 'classic' ? (
        <Path d="M27 32c0-10 6-16 13-16s13 6 13 16c-3.5-4.2-8-6-13-6s-9.5 1.8-13 6z" fill={art.hair} />
      ) : art.hairStyle === 'short' ? (
        <Path d="M27 31c.5-9.5 6-15 13-15s12.5 5.5 13 15c-4-3-8.5-4.5-13-4.5s-9 1.5-13 4.5z" fill={art.hair} />
      ) : (
        <Path d="M26.8 33c.8-9.5 6.2-15.5 13.2-15.5s12.4 6 13.2 15.5c-4.2-4-8.6-6-13.2-6s-9 2-13.2 6z" fill={art.hair} />
      )}
    </Svg>
  );
}

interface Props {
  name: string;
  size?: number;
}

export function AuthorAvatar({ name, size = 40 }: Props) {
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
      <PinterestEditorialAvatar name={name} size={size} />

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
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
    borderWidth: 1.5,
  },
  photo: {
    position: 'absolute',
    top: 0,
    left: 0,
  },
});
