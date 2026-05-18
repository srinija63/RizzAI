import Constants from 'expo-constants';
import { Platform } from 'react-native';
import { RankedReply, RetrievalDebugItem } from '../types/navigation';

// Fallback if Expo can't detect your PC's LAN IP (should match Metro QR host, e.g. 192.168.0.104).
const MOBILE_LAN_API_BASE_URL = 'http://192.168.0.104:8000';
const WEB_LOCALHOST_API_BASE_URL = 'http://127.0.0.1:8000';

/** Same machine IP Metro uses (Expo Go → your PC). */
function resolveApiBaseUrl(): string {
  if (Platform.OS === 'web') {
    return WEB_LOCALHOST_API_BASE_URL;
  }
  const debuggerHost =
    Constants.expoGoConfig?.debuggerHost ??
    Constants.expoConfig?.hostUri?.replace(/^exp:\/\//, '').split('/')[0];
  if (debuggerHost) {
    const host = debuggerHost.split(':')[0];
    if (host && host !== 'localhost' && host !== '127.0.0.1') {
      return `http://${host}:8000`;
    }
  }
  return MOBILE_LAN_API_BASE_URL;
}

const API_BASE_URL = resolveApiBaseUrl();

/** Reply pipeline can run 30–90s on first request (embeddings + LLM). */
const REPLY_TIMEOUT_MS = 120000;
const REQUEST_TIMEOUT_MS = 20000;
const IMAGE_EXTRACT_TIMEOUT_MS = 55000;
const WRITING_TIMEOUT_MS = 55000;

type ReplyApiResponse = {
  replies?: Array<string | { text?: string; label?: string; score?: number }>;
  suggestions?: string[];
  provider_used?: string | null;
  warning?: string | null;
  mode?: 'normal' | 'fallback';
  meta?: {
    latency_ms?: number;
  } | null;
  retrieval_debug?: RetrievalDebugItem[] | null;
};

export type ReplyResult = {
  replies: RankedReply[];
  retrievalDebug?: RetrievalDebugItem[];
  providerUsed?: string | null;
  latencyMs?: number | null;
  warning?: string | null;
};

export class ApiClientError extends Error {
  code:
    | 'TIMEOUT'
    | 'UNAVAILABLE'
    | 'BAD_RESPONSE'
    | 'EMPTY_RESPONSE'
    | 'UNKNOWN';

  constructor(
    message: string,
    code: ApiClientError['code'] = 'UNKNOWN',
  ) {
    super(message);
    this.code = code;
  }
}

function _normalizeReplies(data: ReplyApiResponse): RankedReply[] {
  const seen = new Set<string>();
  const normalized: RankedReply[] = [];

  for (const reply of data.replies ?? data.suggestions ?? []) {
    let text = '';
    let label: string | undefined;
    let score: number | undefined;

    if (typeof reply === 'string') {
      text = reply.trim();
    } else {
      text = (reply.text ?? '').trim();
      label = reply.label;
      score = typeof reply.score === 'number' ? reply.score : undefined;
    }

    if (!text) continue;
    const key = text.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    normalized.push({ text, label, score });
  }

  return normalized;
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string | string[] | { error?: string } };
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail)) return body.detail.join('\n');
    if (body.detail && typeof body.detail === 'object' && 'error' in body.detail) {
      return String((body.detail as { error?: string }).error);
    }
  } catch {
    /* ignore */
  }
  return '';
}

export async function fetchReplySuggestions(
  message: string,
  tone: string,
  explainabilityMode = false,
  replyCount = 3,
  confidenceLevel: 'low' | 'medium' | 'high',
): Promise<ReplyResult> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REPLY_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}/api/reply`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
      body: JSON.stringify({
        conversation_text: message,
        tone,
        retrieval_debug: explainabilityMode,
        reply_count: Math.min(12, Math.max(3, Math.round(replyCount))),
        confidence_level: confidenceLevel,
      }),
    });

    if (!response.ok) {
      const detail = await parseErrorDetail(response);
      if (response.status >= 500) {
        throw new ApiClientError(
          detail || 'The server had an error. Try again in a moment.',
          'UNAVAILABLE',
        );
      }
      throw new ApiClientError(
        detail || `Server returned ${response.status}. Check tone and message.`,
        'BAD_RESPONSE',
      );
    }

    let data: ReplyApiResponse;
    try {
      data = (await response.json()) as ReplyApiResponse;
    } catch {
      throw new ApiClientError('Could not read server response', 'BAD_RESPONSE');
    }

    const replies = _normalizeReplies(data);
    if (!replies.length) {
      throw new ApiClientError('Could not generate replies', 'EMPTY_RESPONSE');
    }

    return {
      replies,
      retrievalDebug: data.retrieval_debug ?? undefined,
      providerUsed: data.provider_used ?? null,
      latencyMs: data.meta?.latency_ms ?? null,
      warning: data.warning ?? (data.mode === 'fallback' ? 'Using fallback AI mode' : null),
    };
  } catch (error) {
    if (error instanceof ApiClientError) {
      throw error;
    }

    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiClientError(
        'Request timed out. The AI may still be loading — try again, or wait for the first run to finish on your PC.',
        'TIMEOUT',
      );
    }

    throw new ApiClientError(
      `Cannot reach the API at ${API_BASE_URL}. Start the backend (uvicorn on port 8000) and use the same Wi‑Fi as this phone.`,
      'UNKNOWN',
    );
  } finally {
    clearTimeout(timeout);
  }
}

type ExtractImageApiResponse = {
  conversation_text?: string;
  warning?: string | null;
};

/** Read chat text from a screenshot (server uses Gemini vision). */
export async function extractConversationFromScreenshot(
  imageBase64: string,
  mimeType: string,
): Promise<{ text: string; warning?: string | null }> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), IMAGE_EXTRACT_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}/api/extract-from-image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        image_base64: imageBase64,
        mime_type: mimeType,
      }),
    });

    if (!response.ok) {
      let detail = '';
      try {
        const errBody = (await response.json()) as { detail?: string | string[] };
        if (typeof errBody.detail === 'string') {
          detail = errBody.detail;
        } else if (Array.isArray(errBody.detail)) {
          detail = errBody.detail.join(' ');
        }
      } catch {
        /* ignore */
      }
      if (response.status >= 500) {
        throw new ApiClientError(
          detail || 'The server had an error. Try again in a moment.',
          'UNAVAILABLE',
        );
      }
      throw new ApiClientError(
        detail || 'Could not read this image.',
        'BAD_RESPONSE',
      );
    }

    const data = (await response.json()) as ExtractImageApiResponse;
    const text = (data.conversation_text ?? '').trim();
    if (!text) {
      throw new ApiClientError('No text was extracted from the image.', 'EMPTY_RESPONSE');
    }
    return { text, warning: data.warning ?? null };
  } catch (error) {
    if (error instanceof ApiClientError) {
      throw error;
    }
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiClientError(
        'Image read timed out. Try a smaller photo or check your network.',
        'TIMEOUT',
      );
    }
    throw new ApiClientError('Could not read this image.', 'UNKNOWN');
  } finally {
    clearTimeout(timeout);
  }
}

export type BioStyleTemplate =
  | 'witty_minimal'
  | 'warm_story'
  | 'bold_confident'
  | 'playful'
  | 'authentic_soft';

type OpenersApiResponse = {
  openers?: string[];
  provider_used?: string | null;
};

type BioApiResponse = {
  bios?: string[];
  provider_used?: string | null;
};

export async function fetchOpeners(
  profileDescription: string,
  tone: 'funny' | 'flirty' | 'confident' | 'direct',
  count = 6,
): Promise<{ openers: string[]; providerUsed: string | null }> {
  if (!tone) {
    throw new ApiClientError('Pick a tone before generating openers.', 'BAD_RESPONSE');
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), WRITING_TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE_URL}/api/openers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        profile_description: profileDescription.trim(),
        tone,
        count: Math.min(10, Math.max(3, Math.round(count))),
      }),
    });
    if (!response.ok) {
      throw new ApiClientError('Could not generate openers', 'BAD_RESPONSE');
    }
    const data = (await response.json()) as OpenersApiResponse;
    const openers = (data.openers ?? []).map((s) => s.trim()).filter(Boolean);
    if (!openers.length) {
      throw new ApiClientError('No openers returned', 'EMPTY_RESPONSE');
    }
    return { openers, providerUsed: data.provider_used ?? null };
  } catch (error) {
    if (error instanceof ApiClientError) throw error;
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiClientError('Request timed out.', 'TIMEOUT');
    }
    throw new ApiClientError('Could not generate openers', 'UNKNOWN');
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchBioVariants(
  aboutText: string,
  styleTemplate: BioStyleTemplate,
  variantCount = 3,
): Promise<{ bios: string[]; providerUsed: string | null }> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), WRITING_TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE_URL}/api/bio`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        about_text: aboutText.trim(),
        style_template: styleTemplate,
        variant_count: Math.min(5, Math.max(1, Math.round(variantCount))),
      }),
    });
    if (!response.ok) {
      throw new ApiClientError('Could not generate bios', 'BAD_RESPONSE');
    }
    const data = (await response.json()) as BioApiResponse;
    const seen = new Set<string>();
    const bios: string[] = [];
    for (const raw of data.bios ?? []) {
      const text = raw.trim();
      if (!text) continue;
      const key = text.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      bios.push(text);
    }
    if (!bios.length) {
      throw new ApiClientError('No bios returned', 'EMPTY_RESPONSE');
    }
    return { bios, providerUsed: data.provider_used ?? null };
  } catch (error) {
    if (error instanceof ApiClientError) throw error;
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiClientError('Request timed out.', 'TIMEOUT');
    }
    throw new ApiClientError('Could not generate bios', 'UNKNOWN');
  } finally {
    clearTimeout(timeout);
  }
}
