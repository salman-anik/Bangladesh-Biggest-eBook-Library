import React from 'react';
import {
  Image,
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
  ArrowLeftIcon,
  BookOpenIcon,
  GithubIcon,
  GlobeIcon,
  LockIcon,
  MailIcon,
} from '../components/Icons';
import { useAppTheme } from '../context/ThemeContext';
import { CURRENT_APP_VERSION } from '../services/updateService';

interface Props {
  visible: boolean;
  onClose: () => void;
}

const REPO_URL = 'https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library';

export function DeveloperScreen({ visible, onClose }: Props) {
  const { theme, fs } = useAppTheme();

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={[styles.root, { backgroundColor: theme.bg }]} edges={['top', 'bottom']}>
        {/* Top Navigation Bar */}
        <View style={[styles.topBar, { borderBottomColor: theme.border }]}>
          <TouchableOpacity
            style={[styles.backBtn, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
            onPress={onClose}
            activeOpacity={0.82}
            accessibilityLabel="Back to Settings"
          >
            <ArrowLeftIcon size={18} color={theme.ink} />
          </TouchableOpacity>
          <Text style={[styles.topTitle, { color: theme.ink, fontSize: fs(18) }]}>
            Developer, Policy &amp; Copyright
          </Text>
        </View>

        <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          {/* Developer Profile Card */}
          <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
            <Text style={[styles.eyebrow, { color: theme.accent }]}>DEVELOPER &amp; MAINTAINER</Text>

            <View style={styles.profileRow}>
              <Image
                source={require('../../assets/developer-profile.png')}
                style={[styles.avatar, { borderColor: theme.accent, backgroundColor: theme.surfaceAlt }]}
                resizeMode="cover"
              />
              <View style={styles.identityCol}>
                <Text style={[styles.devName, { color: theme.ink, fontSize: fs(20) }]}>Salman Anik</Text>
                <Text style={[styles.devTagline, { color: theme.cream, fontSize: fs(12) }]}>
                  CSE Student · Data Science Enthusiast · Python Developer
                </Text>
              </View>
            </View>

            <Text style={[styles.bodyText, { color: theme.muted, fontSize: fs(13) }]}>
              Computer Science &amp; Engineering student at East West University, Dhaka, focused on
              Python, SQL, Data Science, and building open-source tools including AnaBook
              (Bangladesh&apos;s Biggest eBook Library) and AnaPharm.
            </Text>

            <View style={[styles.metaBox, { backgroundColor: theme.surfaceAlt, borderColor: theme.borderSubtle }]}>
              <View style={styles.metaRow}>
                <Text style={[styles.metaLabel, { color: theme.muted }]}>University</Text>
                <Text style={[styles.metaValue, { color: theme.ink }]}>East West University (B.Sc. in CSE)</Text>
              </View>
              <View style={[styles.divider, { backgroundColor: theme.border }]} />
              <View style={styles.metaRow}>
                <Text style={[styles.metaLabel, { color: theme.muted }]}>Location</Text>
                <Text style={[styles.metaValue, { color: theme.ink }]}>Dhaka, Bangladesh</Text>
              </View>
            </View>

            <View style={styles.linksRow}>
              <TouchableOpacity
                style={[styles.linkPrimary, { backgroundColor: theme.accent }]}
                onPress={() => void Linking.openURL('https://salmananik.vercel.app/')}
                activeOpacity={0.85}
              >
                <GlobeIcon size={16} color={theme.creamInk} />
                <Text style={[styles.linkPrimaryText, { color: theme.creamInk }]}>Portfolio</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.linkSecondary, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
                onPress={() => void Linking.openURL('https://github.com/salman-anik')}
                activeOpacity={0.85}
              >
                <GithubIcon size={16} color={theme.cream} />
                <Text style={[styles.linkSecondaryText, { color: theme.cream }]}>GitHub</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.linkSecondary, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
                onPress={() => void Linking.openURL('mailto:salmananik.bd@gmail.com')}
                activeOpacity={0.85}
                accessibilityLabel="Email Developer"
              >
                <MailIcon size={16} color={theme.cream} />
              </TouchableOpacity>
            </View>
          </View>

          {/* About AnaBook Card */}
          <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
            <View style={styles.aboutBrandRow}>
              <Image source={require('../../assets/icon.png')} style={styles.aboutLogo} resizeMode="cover" />
              <View style={{ flex: 1 }}>
                <Text style={[styles.eyebrow, { color: theme.accent }]}>ABOUT ANABOOK</Text>
                <Text style={[styles.cardTitle, { color: theme.ink, fontSize: fs(15.5) }]}>
                  AnaBook eBook Library
                </Text>
              </View>
            </View>
            <View style={[styles.metaBox, { backgroundColor: theme.surfaceAlt, borderColor: theme.borderSubtle }]}>
              <View style={styles.metaRow}>
                <Text style={[styles.metaLabel, { color: theme.muted }]}>Application</Text>
                <Text style={[styles.metaValue, { color: theme.ink }]}>AnaBook eBook Library</Text>
              </View>
              <View style={[styles.divider, { backgroundColor: theme.border }]} />
              <View style={styles.metaRow}>
                <Text style={[styles.metaLabel, { color: theme.muted }]}>Version</Text>
                <Text style={[styles.metaValue, { color: theme.accent }]}>v{CURRENT_APP_VERSION}</Text>
              </View>
            </View>

            <TouchableOpacity
              style={[styles.repoBtn, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}
              onPress={() => void Linking.openURL(REPO_URL)}
              activeOpacity={0.84}
            >
              <GithubIcon size={15} color={theme.ink} />
              <Text style={[styles.repoBtnText, { color: theme.ink, fontSize: fs(12.5) }]}>
                View Project Repository on GitHub
              </Text>
            </TouchableOpacity>
          </View>

          {/* Privacy Policy Card */}
          <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
            <View style={styles.sectionHead}>
              <LockIcon size={17} color={theme.accent} />
              <Text style={[styles.cardTitle, { color: theme.ink, fontSize: fs(15.5) }]}>Privacy Policy</Text>
            </View>

            <View style={styles.bulletBlock}>
              <Text style={[styles.bulletTitle, { color: theme.ink, fontSize: fs(13) }]}>
                1. Zero Personal Data Collection
              </Text>
              <Text style={[styles.bodyText, { color: theme.muted, fontSize: fs(12.5) }]}>
                AnaBook requires no account sign-in, email, phone number, or personal profile. The
                app does not run advertising SDKs or collect analytics tracking your identity.
              </Text>
            </View>

            <View style={styles.bulletBlock}>
              <Text style={[styles.bulletTitle, { color: theme.ink, fontSize: fs(13) }]}>
                2. Local-Only Storage
              </Text>
              <Text style={[styles.bodyText, { color: theme.muted, fontSize: fs(12.5) }]}>
                Reading progress, bookmarks, daily reading streaks, theme settings, and downloaded
                offline books stay strictly on your own device and can be cleared at any time.
              </Text>
            </View>

            <View style={styles.bulletBlock}>
              <Text style={[styles.bulletTitle, { color: theme.ink, fontSize: fs(13) }]}>
                3. Network Requests
              </Text>
              <Text style={[styles.bodyText, { color: theme.muted, fontSize: fs(12.5) }]}>
                Catalog updates and app version checks fetch public metadata from the official
                project repository on GitHub/Vercel. Opening or downloading books connects directly
                to Google Drive, and optional Wikipedia links open in your browser.
              </Text>
            </View>
          </View>

          {/* Copyright & DMCA Notice Card */}
          <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
            <View style={styles.sectionHead}>
              <BookOpenIcon size={17} color={theme.accent} />
              <Text style={[styles.cardTitle, { color: theme.ink, fontSize: fs(15.5) }]}>
                Copyright &amp; DMCA Policy
              </Text>
            </View>

            <View style={styles.bulletBlock}>
              <Text style={[styles.bulletTitle, { color: theme.ink, fontSize: fs(13) }]}>
                1. Ownership of Literary Works
              </Text>
              <Text style={[styles.bodyText, { color: theme.muted, fontSize: fs(12.5) }]}>
                All books, covers, and author biographies remain the intellectual property of their
                respective authors, translators, and publishers. AnaBook does not claim ownership over
                indexed third-party literary works.
              </Text>
            </View>

            <View style={styles.bulletBlock}>
              <Text style={[styles.bulletTitle, { color: theme.ink, fontSize: fs(13) }]}>
                2. Educational &amp; Archival Mission
              </Text>
              <Text style={[styles.bodyText, { color: theme.muted, fontSize: fs(12.5) }]}>
                This digital library is curated non-commercially for personal study, research, and the
                preservation of Bengali, academic, religious, and classic world literature.
              </Text>
            </View>

            <View style={styles.bulletBlock}>
              <Text style={[styles.bulletTitle, { color: theme.ink, fontSize: fs(13) }]}>
                3. Content Removal / DMCA Requests
              </Text>
              <Text style={[styles.bodyText, { color: theme.muted, fontSize: fs(12.5) }]}>
                If you are a rightful copyright holder and want any work removed from the index or
                archive, email salmananik.bd@gmail.com with the book title and proof of ownership for
                prompt action.
              </Text>
            </View>

            <View style={[styles.footerBanner, { backgroundColor: theme.surfaceAlt, borderColor: theme.borderSubtle }]}>
              <Text style={[styles.footerText, { color: theme.cream, fontSize: fs(12) }]}>
                © 2026 Salman Anik · AnaBook Mobile App
              </Text>
            </View>
          </View>
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 18,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  backBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  topTitle: { fontWeight: '800', flex: 1 },
  content: { paddingHorizontal: 18, paddingTop: 14, paddingBottom: 36, gap: 14 },
  card: {
    borderRadius: 20,
    borderWidth: 1,
    padding: 16,
    gap: 12,
  },
  eyebrow: {
    fontSize: 10.5,
    fontWeight: '800',
    letterSpacing: 0.9,
  },
  sectionHead: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  aboutBrandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  aboutLogo: {
    width: 44,
    height: 44,
    borderRadius: 12,
  },
  cardTitle: { fontWeight: '800' },
  profileRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  avatar: {
    width: 82,
    height: 82,
    borderRadius: 41,
    borderWidth: 2,
  },
  identityCol: { flex: 1, gap: 4 },
  devName: { fontWeight: '800' },
  devTagline: { fontWeight: '600', lineHeight: 17 },
  bodyText: { lineHeight: 19 },
  metaBox: {
    borderRadius: 14,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 8,
    gap: 7,
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
  },
  metaLabel: { fontSize: 11.5, fontWeight: '700' },
  metaValue: { fontSize: 12, fontWeight: '700', flexShrink: 1, textAlign: 'right' },
  divider: { height: StyleSheet.hairlineWidth },
  linksRow: { flexDirection: 'row', gap: 8 },
  linkPrimary: {
    flex: 1.4,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderRadius: 14,
    paddingVertical: 11,
  },
  linkPrimaryText: { fontSize: 12.5, fontWeight: '800' },
  linkSecondary: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderWidth: 1,
    borderRadius: 14,
    paddingVertical: 11,
  },
  linkSecondaryText: { fontSize: 12, fontWeight: '700' },
  repoBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderWidth: 1,
    borderRadius: 14,
    paddingVertical: 11,
  },
  repoBtnText: { fontWeight: '700' },
  bulletBlock: { gap: 4 },
  bulletTitle: { fontWeight: '700' },
  footerBanner: {
    borderRadius: 12,
    borderWidth: 1,
    paddingVertical: 10,
    paddingHorizontal: 12,
    alignItems: 'center',
    marginTop: 2,
  },
  footerText: { fontWeight: '700' },
});
