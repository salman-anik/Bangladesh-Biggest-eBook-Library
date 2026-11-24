import React, { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Modal,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import { useAppTheme } from '../context/ThemeContext';
import {
  type AppUpdateInfo,
  cleanupDownloadedUpdate,
  downloadAppUpdateApk,
  installAppUpdate,
} from '../services/updateService';
import { CloseIcon, DownloadIcon } from './Icons';

interface Props {
  visible: boolean;
  updateInfo: AppUpdateInfo | null;
  onClose: () => void;
}

type UpdateStatus = 'idle' | 'downloading' | 'ready' | 'installing' | 'error';

export function AppUpdateModal({ visible, updateInfo, onClose }: Props) {
  const { theme, fs } = useAppTheme();
  const [status, setStatus] = useState<UpdateStatus>('idle');
  const [progress, setProgress] = useState(0);
  const [downloadedBytes, setDownloadedBytes] = useState(0);
  const [totalBytes, setTotalBytes] = useState(0);
  const [downloadedUri, setDownloadedUri] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!updateInfo) return null;

  const handleStartDownload = async () => {
    const apkUrl = updateInfo.apkDownloadUrl || updateInfo.downloadUrl;
    if (!apkUrl) {
      Alert.alert('Download Error', 'No valid download link found.');
      return;
    }

    setStatus('downloading');
    setProgress(0);
    setErrorMessage(null);

    try {
      const uri = await downloadAppUpdateApk(apkUrl, (fraction, written, total) => {
        setProgress(fraction);
        setDownloadedBytes(written);
        setTotalBytes(total);
      });
      setDownloadedUri(uri);
      setStatus('ready');
    } catch (err) {
      setStatus('error');
      setErrorMessage(err instanceof Error ? err.message : String(err));
    }
  };

  const handleInstall = async () => {
    setStatus('installing');
    try {
      await installAppUpdate(downloadedUri || undefined);
      // Once launched installer, clean up state
      setStatus('idle');
      setDownloadedUri(null);
      onClose();
    } catch (err) {
      setStatus('error');
      setErrorMessage(err instanceof Error ? err.message : String(err));
    }
  };

  const handleCancelAndCleanup = async () => {
    if (status === 'ready' || downloadedUri) {
      await cleanupDownloadedUpdate();
    }
    setStatus('idle');
    setDownloadedUri(null);
    setProgress(0);
    setErrorMessage(null);
    onClose();
  };

  const formatSize = (bytes: number) => {
    if (bytes <= 0) return '0 MB';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={handleCancelAndCleanup}
    >
      <View style={styles.backdrop}>
        <View style={[styles.dialog, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          {/* Header */}
          <View style={styles.header}>
            <View style={{ flex: 1 }}>
              <Text style={[styles.title, { color: theme.ink, fontSize: fs(18) }]}>
                Update AnaBook
              </Text>
              <Text style={[styles.versionBadge, { color: theme.accent, fontSize: fs(13) }]}>
                v{updateInfo.currentVersion} ➔ v{updateInfo.latestVersion}
              </Text>
            </View>
            {status !== 'downloading' && (
              <TouchableOpacity
                onPress={handleCancelAndCleanup}
                style={[styles.closeBtn, { backgroundColor: theme.surfaceAlt }]}
                hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
              >
                <CloseIcon color={theme.ink} size={16} />
              </TouchableOpacity>
            )}
          </View>

          {/* Release Notes */}
          {updateInfo.releaseNotes ? (
            <View style={[styles.notesBox, { backgroundColor: theme.surfaceAlt, borderColor: theme.border }]}>
              <Text style={[styles.notesHeading, { color: theme.muted, fontSize: fs(11) }]}>
                WHAT&apos;S NEW
              </Text>
              <Text style={[styles.notesText, { color: theme.ink, fontSize: fs(12.5) }]}>
                {updateInfo.releaseNotes}
              </Text>
            </View>
          ) : null}

          {/* Progress / Status display */}
          {status === 'downloading' && (
            <View style={styles.progressContainer}>
              <View style={styles.progressMeta}>
                <Text style={[styles.progressLabel, { color: theme.ink, fontSize: fs(12) }]}>
                  Downloading update… {Math.round(progress * 100)}%
                </Text>
                <Text style={[styles.progressBytes, { color: theme.muted, fontSize: fs(11.5) }]}>
                  {formatSize(downloadedBytes)} / {totalBytes > 0 ? formatSize(totalBytes) : '…'}
                </Text>
              </View>
              <View style={[styles.progressBarTrack, { backgroundColor: theme.border }]}>
                <View
                  style={[
                    styles.progressBarFill,
                    { backgroundColor: theme.accent, width: `${Math.round(progress * 100)}%` },
                  ]}
                />
              </View>
            </View>
          )}

          {status === 'ready' && (
            <View style={[styles.readyBanner, { backgroundColor: theme.surfaceAlt }]}>
              <Text style={[styles.readyText, { color: theme.accent, fontSize: fs(12.5) }]}>
                ✓ Download complete! Tap Install Now to update.
              </Text>
              <Text style={[styles.cleanupNote, { color: theme.muted, fontSize: fs(11) }]}>
                The temporary APK will be automatically deleted after installation to save storage.
              </Text>
            </View>
          )}

          {status === 'error' && (
            <View style={[styles.errorBox, { backgroundColor: theme.surfaceAlt }]}>
              <Text style={[styles.errorText, { color: '#EF4444', fontSize: fs(12) }]}>
                {errorMessage || 'Failed to download or install update.'}
              </Text>
            </View>
          )}

          {/* Action Buttons */}
          <View style={styles.actionsRow}>
            {status === 'idle' || status === 'error' ? (
              <>
                <TouchableOpacity
                  style={[styles.secondaryBtn, { borderColor: theme.border }]}
                  onPress={handleCancelAndCleanup}
                  activeOpacity={0.8}
                >
                  <Text style={[styles.secondaryBtnText, { color: theme.muted, fontSize: fs(13) }]}>
                    Later
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.primaryBtn, { backgroundColor: theme.accent }]}
                  onPress={handleStartDownload}
                  activeOpacity={0.85}
                >
                  <DownloadIcon color={theme.creamInk} size={15} />
                  <Text style={[styles.primaryBtnText, { color: theme.creamInk, fontSize: fs(13) }]}>
                    Download Update
                  </Text>
                </TouchableOpacity>
              </>
            ) : null}

            {status === 'downloading' ? (
              <View style={styles.downloadingRow}>
                <ActivityIndicator size="small" color={theme.accent} />
                <Text style={[styles.downloadingText, { color: theme.muted, fontSize: fs(12) }]}>
                  Please keep AnaBook open while downloading…
                </Text>
              </View>
            ) : null}

            {status === 'ready' ? (
              <>
                <TouchableOpacity
                  style={[styles.secondaryBtn, { borderColor: theme.border }]}
                  onPress={handleCancelAndCleanup}
                  activeOpacity={0.8}
                >
                  <Text style={[styles.secondaryBtnText, { color: theme.muted, fontSize: fs(13) }]}>
                    Cancel
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.primaryBtn, { backgroundColor: theme.accent }]}
                  onPress={handleInstall}
                  activeOpacity={0.85}
                >
                  <Text style={[styles.primaryBtnText, { color: theme.creamInk, fontSize: fs(13) }]}>
                    Install Now
                  </Text>
                </TouchableOpacity>
              </>
            ) : null}

            {status === 'installing' ? (
              <View style={styles.downloadingRow}>
                <ActivityIndicator size="small" color={theme.accent} />
                <Text style={[styles.downloadingText, { color: theme.muted, fontSize: fs(12) }]}>
                  Opening package installer…
                </Text>
              </View>
            ) : null}
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.65)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  dialog: {
    width: '100%',
    maxWidth: 380,
    borderRadius: 24,
    borderWidth: 1,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.15,
    shadowRadius: 16,
    elevation: 8,
    gap: 16,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
  },
  title: {
    fontWeight: '800',
    letterSpacing: -0.3,
  },
  versionBadge: {
    fontWeight: '700',
    marginTop: 2,
  },
  closeBtn: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  notesBox: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 12,
    gap: 4,
  },
  notesHeading: {
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  notesText: {
    lineHeight: 18,
  },
  progressContainer: {
    gap: 8,
  },
  progressMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  progressLabel: {
    fontWeight: '700',
  },
  progressBytes: {
    fontWeight: '600',
  },
  progressBarTrack: {
    height: 8,
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 4,
  },
  readyBanner: {
    borderRadius: 14,
    padding: 12,
    gap: 4,
  },
  readyText: {
    fontWeight: '700',
  },
  cleanupNote: {
    fontWeight: '500',
    lineHeight: 15,
  },
  errorBox: {
    borderRadius: 14,
    padding: 10,
  },
  errorText: {
    fontWeight: '600',
  },
  actionsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 10,
    marginTop: 4,
  },
  secondaryBtn: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 14,
    borderWidth: 1,
  },
  secondaryBtnText: {
    fontWeight: '700',
  },
  primaryBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderRadius: 14,
  },
  primaryBtnText: {
    fontWeight: '800',
  },
  downloadingRow: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 6,
  },
  downloadingText: {
    fontWeight: '600',
  },
});
