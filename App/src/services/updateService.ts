// eslint-disable-next-line @typescript-eslint/no-var-requires
const APP_CONFIG = require('../../app.json') as {
  expo?: {
    version?: string;
    android?: { versionCode?: number };
  };
};

export const CURRENT_APP_VERSION = APP_CONFIG?.expo?.version || '1.0.0';
export const CURRENT_VERSION_CODE = APP_CONFIG?.expo?.android?.versionCode ?? 1;

const DEFAULT_DOWNLOAD_URL =
  'https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library/releases/latest';

const VERSION_ENDPOINTS = [
  'https://anabook-bd.vercel.app/app-version.json',
  'https://salman-anik.github.io/Bangladesh-Biggest-eBook-Library/app-version.json',
];

export interface AppUpdateInfo {
  hasUpdate: boolean;
  currentVersion: string;
  latestVersion: string;
  versionCode: number;
  releaseNotes: string;
  downloadUrl: string;
  checkedAt: string;
  error?: string;
}

interface RemoteVersionManifest {
  latestVersion?: string;
  versionCode?: number;
  downloadUrl?: string;
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

      return {
        hasUpdate,
        currentVersion: CURRENT_APP_VERSION,
        latestVersion,
        versionCode: remoteCode || CURRENT_VERSION_CODE,
        releaseNotes: data.releaseNotes || '',
        downloadUrl: data.downloadUrl || DEFAULT_DOWNLOAD_URL,
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
    downloadUrl: DEFAULT_DOWNLOAD_URL,
    checkedAt,
    error: lastError,
  };
}
