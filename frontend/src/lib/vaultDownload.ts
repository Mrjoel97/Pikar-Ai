// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

export const DEFAULT_VAULT_DOWNLOAD_BUCKET = 'knowledge-vault';
const SIGN_URL_TIMEOUT_MS = 5000;

interface SignedUrlResponse {
  items?: Array<{ path: string; signedUrl: string | null }>;
  error?: string;
}

export async function getVaultSignedUrl({
  bucket = DEFAULT_VAULT_DOWNLOAD_BUCKET,
  path,
  timeoutMs = SIGN_URL_TIMEOUT_MS,
}: {
  bucket?: string;
  path: string;
  timeoutMs?: number;
}): Promise<string> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch('/api/vault/sign-urls', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({ bucket, paths: [path] }),
    });
    const body = (await response.json().catch(() => ({}))) as SignedUrlResponse;
    if (!response.ok) {
      throw new Error(body.error || `Signed URL request failed (${response.status})`);
    }

    const signedUrl = body.items?.find((item) => item.path === path)?.signedUrl;
    if (!signedUrl) {
      throw new Error('No signed URL returned');
    }
    return signedUrl;
  } finally {
    window.clearTimeout(timer);
  }
}

export async function downloadUrlAsFile(url: string, filename: string): Promise<void> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Download failed (${response.status})`);
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
}

export async function downloadVaultStorageFile({
  bucket = DEFAULT_VAULT_DOWNLOAD_BUCKET,
  path,
  filename,
}: {
  bucket?: string;
  path: string;
  filename: string;
}): Promise<void> {
  const signedUrl = await getVaultSignedUrl({ bucket, path });
  await downloadUrlAsFile(signedUrl, filename);
}
