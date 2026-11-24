import React from 'react';
import {
  Linking,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import { useAppTheme } from '../context/ThemeContext';
import { AuthorAvatar } from './AuthorAvatar';
import { CloseIcon, GlobeIcon } from './Icons';

interface Props {
  visible: boolean;
  authorName: string;
  group: string;
  bookCount: number;
  subfolderCount: number;
  shortDesc?: string;
  bio?: string;
  wikiUrl?: string;
  onClose: () => void;
}

export function AuthorDetailModal({
  visible,
  authorName,
  group,
  bookCount,
  subfolderCount,
  shortDesc,
  bio,
  wikiUrl,
  onClose,
}: Props) {
  const { theme, fs } = useAppTheme();

  const displayBio =
    (bio || '').trim() ||
    `Explore ${bookCount.toLocaleString()} digitized ${bookCount === 1 ? 'book' : 'books'} by ${authorName} under ${group}.`;

  return (
    <Modal visible={visible} animationType="fade" transparent onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <View style={styles.topRow}>
            <Text style={[styles.eyebrow, { color: theme.accent }]}>AUTHOR DETAILS</Text>
            <TouchableOpacity
              style={[styles.closeCircle, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
              onPress={onClose}
              accessibilityLabel="Close author details"
            >
              <CloseIcon size={16} color={theme.ink} />
            </TouchableOpacity>
          </View>

          <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollBody}>
            <View style={styles.identityCenter}>
              <AuthorAvatar name={authorName} size={84} />
              <Text style={[styles.authorName, { color: theme.ink, fontSize: fs(20) }]}>
                {authorName}
              </Text>
              {shortDesc ? (
                <Text style={[styles.shortDesc, { color: theme.cream, fontSize: fs(12.5) }]}>
                  {shortDesc}
                </Text>
              ) : null}

              <View style={styles.pillsRow}>
                {group ? (
                  <View style={[styles.groupPill, { backgroundColor: theme.accentSoft, borderColor: theme.accent }]}>
                    <Text style={[styles.groupPillText, { color: theme.accent, fontSize: fs(11) }]}>
                      {group}
                    </Text>
                  </View>
                ) : null}
                <View style={[styles.statPill, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
                  <Text style={[styles.statPillText, { color: theme.ink, fontSize: fs(11) }]}>
                    {bookCount.toLocaleString()} {bookCount === 1 ? 'Book' : 'Books'}
                  </Text>
                </View>
                {subfolderCount > 0 ? (
                  <View style={[styles.statPill, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
                    <Text style={[styles.statPillText, { color: theme.ink, fontSize: fs(11) }]}>
                      {subfolderCount} {subfolderCount === 1 ? 'Section' : 'Sections'}
                    </Text>
                  </View>
                ) : null}
              </View>
            </View>

            <View style={[styles.bioBox, { backgroundColor: theme.surfaceAlt, borderColor: theme.borderSubtle }]}>
              <Text style={[styles.bioLabel, { color: theme.muted }]}>ABOUT THE AUTHOR</Text>
              <Text style={[styles.bioText, { color: theme.ink, fontSize: fs(13) }]}>
                {displayBio}
              </Text>
            </View>
          </ScrollView>

          <View style={styles.actionsRow}>
            {wikiUrl ? (
              <TouchableOpacity
                style={[styles.wikiBtn, { backgroundColor: theme.accent }]}
                onPress={() => void Linking.openURL(wikiUrl)}
                activeOpacity={0.85}
              >
                <GlobeIcon size={16} color={theme.creamInk} />
                <Text style={[styles.wikiBtnText, { color: theme.creamInk, fontSize: fs(12.5) }]}>
                  Read on Wikipedia
                </Text>
              </TouchableOpacity>
            ) : null}

            <TouchableOpacity
              style={[
                styles.closeBtn,
                {
                  backgroundColor: theme.surfaceAlt,
                  borderColor: theme.border,
                  flex: wikiUrl ? 0.7 : 1,
                },
              ]}
              onPress={onClose}
              activeOpacity={0.84}
            >
              <Text style={[styles.closeBtnText, { color: theme.ink, fontSize: fs(12.5) }]}>Close</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.68)',
    justifyContent: 'center',
    paddingHorizontal: 18,
  },
  card: {
    borderRadius: 24,
    borderWidth: 1,
    padding: 18,
    gap: 12,
    maxHeight: '84%',
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  eyebrow: {
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
  scrollBody: {
    gap: 14,
    paddingBottom: 4,
  },
  identityCenter: {
    alignItems: 'center',
    gap: 8,
  },
  authorName: {
    fontWeight: '800',
    textAlign: 'center',
  },
  shortDesc: {
    fontWeight: '600',
    textAlign: 'center',
    lineHeight: 18,
  },
  pillsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 6,
    marginTop: 2,
  },
  groupPill: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  groupPillText: { fontWeight: '700' },
  statPill: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  statPillText: { fontWeight: '700' },
  bioBox: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 13,
    gap: 6,
  },
  bioLabel: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.8,
  },
  bioText: {
    lineHeight: 20,
  },
  actionsRow: {
    flexDirection: 'row',
    gap: 8,
  },
  wikiBtn: {
    flex: 1.4,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderRadius: 14,
    paddingVertical: 11,
  },
  wikiBtnText: { fontWeight: '800' },
  closeBtn: {
    borderWidth: 1,
    borderRadius: 14,
    paddingVertical: 11,
    alignItems: 'center',
    justifyContent: 'center',
  },
  closeBtnText: { fontWeight: '700' },
});
