import { Linking, Platform } from 'react-native';
import * as FileSystem from 'expo-file-system/legacy';
import * as IntentLauncher from 'expo-intent-launcher';
import * as Sharing from 'expo-sharing';

// eslint-disable-next-line @typescript-eslint/no-var-requires
const APP_CONFIG = require('../../app.json') as {
  expo?: {
    version?: string;
    android?: { versionCode?: number };
  };
};

export const CURRENT_APP_VERSION = APP_CONFIG?.expo?.version || '1.1.1';
export const CURRENT_VERSION_CODE = APP_CONFIG?.expo?.android?.versionCode ?? 3;

const DEFAULT_RELEASE_PAGE =
  'https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library/releases/latest';

const VERSION_ENDPOINTS = [
  'https://anabook-bd.vercel.app/app-version.json',
  'https://salman-anik.github.io/Bangladesh-Biggest-eBook-Library/app-version.json',
];

const APK_CACHE_FILE = `${FileSystem.cacheDirectory ?? ''}anabook-update.apk`;

export interface AppUpdateInfo {
  hasUpdate: boolean;
  currentVersion: string;
  latestVersion: string;
  versionCode: number;
  releaseNotes: string;
  downloadUrl: string;
  apkDownloadUrl?: string;
  checkedAt: string;
  error?: string;
}

interface RemoteVersionManifest {
  latestVersion?: string;
  versionCode?: number;
  downloadUrl?: string;
  apkDownloadUrl?: string;
  releaseNotes?: string;
}

export function compareSemver(a: string, b: string): number {
  const pa = (a || '0.0.0').replace(/^v/i, '').split('.').map((x) => parseInt(x, 10) || 0);
  const pb = (b || '0.0.0').replace(/^v/i, '').split('.').map((x) => parseInt(x, 10) || 0);
  const len = Math.max(pa.length, pb.length, 3);
  for (let i = 0; i < len; i++) {
    const da = pa[i] || 0;
    const db = pb[i] || 0;
    if (da > db) return 1;
    if (da < db) return -1;
  }
  return 0;
}

async function fetchManifest(baseUrl: string): Promise<RemoteVersionManifest> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);
  try {
    const res = await fetch(`${baseUrl}?t=${Date.now()}`, {
      cache: 'no-store',
      signal: controller.signal,
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    return (await res.json()) as RemoteVersionManifest;
  } finally {
    clearTimeout(timer);
  }
}

export async function checkForAppUpdate(): Promise<AppUpdateInfo> {
  const checkedAt = new Date().toISOString();
  let lastError = 'Unable to reach update server.';

  for (const endpoint of VERSION_ENDPOINTS) {
    try {
      const data = await fetchManifest(endpoint);
      const latestVersion = (data.latestVersion || CURRENT_APP_VERSION).trim();
      const remoteCode = Number(data.versionCode || 0);
      const hasUpdate =
        compareSemver(latestVersion, CURRENT_APP_VERSION) > 0 ||
        remoteCode > CURRENT_VERSION_CODE;

      const directApk =
        data.apkDownloadUrl ||
        (latestVersion
          ? `https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library/releases/download/v${latestVersion}/AnaBook.apk`
          : undefined);

      return {
        hasUpdate,
        currentVersion: CURRENT_APP_VERSION,
        latestVersion,
        versionCode: remoteCode || CURRENT_VERSION_CODE,
        releaseNotes: data.releaseNotes || '',
        downloadUrl: data.downloadUrl || DEFAULT_RELEASE_PAGE,
        apkDownloadUrl: directApk,
        checkedAt,
      };
    } catch (err) {
      lastError = err instanceof Error ? err.message : String(err);
    }
  }

  return {
    hasUpdate: false,
    currentVersion: CURRENT_APP_VERSION,
    latestVersion: CURRENT_APP_VERSION,
    versionCode: CURRENT_VERSION_CODE,
    releaseNotes: '',
    downloadUrl: DEFAULT_RELEASE_PAGE,
    checkedAt,
    error: lastError,
  };
}

/**
 * Clean up any previously downloaded temporary update APK files.
 */
export async function cleanupDownloadedUpdate(): Promise<void> {
  try {
    const info = await FileSystem.getInfoAsync(APK_CACHE_FILE);
    if (info.exists) {
      await FileSystem.deleteAsync(APK_CACHE_FILE, { idempotent: true });
    }
  } catch {
    // Non-critical cleanup error
  }
}

/**
 * Downloads the update APK into cache directory with progress reporting.
 */
export async function downloadAppUpdateApk(
  apkUrl: string,
  onProgress?: (progressFraction: number, receivedBytes: number, totalBytes: number) => void
): Promise<string> {
  // Always clean previous apk first
  await cleanupDownloadedUpdate();

  const downloadResumable = FileSystem.createDownloadResumable(
    apkUrl,
    APK_CACHE_FILE,
    {},
    (downloadProgress) => {
      const total = downloadProgress.totalBytesExpectedToWrite;
      const written = downloadProgress.totalBytesWritten;
      const fraction = total > 0 ? Math.min(1, Math.max(0, written / total)) : 0;
      onProgress?.(fraction, written, total);
    }
  );

  const result = await downloadResumable.downloadAsync();
  if (!result || !result.uri) {
    throw new Error('Failed to complete APK download');
  }

  const fileInfo = await FileSystem.getInfoAsync(result.uri);
  if (!fileInfo.exists || fileInfo.size === 0) {
    throw new Error('Downloaded APK file is empty or missing');
  }

  return result.uri;
}

/**
 * Launches the Android package installer for the downloaded APK,
 * then cleans up the downloaded file.
 */
export async function installAppUpdate(apkLocalUri?: string): Promise<void> {
  const fileUri = apkLocalUri || APK_CACHE_FILE;
  const fileInfo = await FileSystem.getInfoAsync(fileUri);
  if (!fileInfo.exists) {
    throw new Error('Update file not found. Please download the update again.');
  }

  try {
    if (Platform.OS === 'android') {
      // Obtain content:// URI for the FileProvider
      const contentUri = await FileSystem.getContentUriAsync(fileUri);
      await IntentLauncher.startActivityAsync('android.intent.action.VIEW', {
        data: contentUri,
        flags: 1, // FLAG_GRANT_READ_URI_PERMISSION
        type: 'application/vnd.android.package-archive',
      });
    } else {
      // iOS / Web fallback
      const canShare = await Sharing.isAvailableAsync();
      if (canShare) {
        await Sharing.shareAsync(fileUri, {
          mimeType: 'application/vnd.android.package-archive',
          dialogTitle: 'Install AnaBook Update',
        });
      } else {
        await Linking.openURL(DEFAULT_RELEASE_PAGE);
      }
    }
  } finally {
    // Clean up temporary downloaded APK so it doesn't waste storage space
    setTimeout(() => {
      void cleanupDownloadedUpdate();
    }, 1500);
  }
}
