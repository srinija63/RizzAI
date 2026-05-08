import { Platform } from 'react-native';
import { RankedReply, RetrievalDebugItem } from '../types/navigation';

// Backend URL configuration:
// - Web (browser on your laptop): keep localhost.
// - Mobile (Expo Go on phone): set this to your laptop's LAN IP.
const MOBILE_LAN_API_BASE_URL = 'http://192.168.0.100:8000';
const WEB_LOCALHOST_API_BASE_URL = 'http://127.0.0.1:8000';

const API_BASE_URL =
  Platform.OS === 'web' ? WEB_LOCALHOST_API_BASE_URL : MOBILE_LAN_API_BASE_URL;

const REQUEST_TIMEOUT_MS = 15000;

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
  const normalized = (data.replies ?? data.suggestions ?? [])
    .map((reply) => {
      if (typeof reply === 'string') {
        const text = reply.trim();
        return text ? { text } : null;
      }
      const text = (reply.text ?? '').trim();
      if (!text) return null;
      return {
        text,
        label: reply.label,
        score: typeof reply.score === 'number' ? reply.score : undefined,
      };
    })
    .filter((item): item is RankedReply => Boolean(item));

  return normalized;
}

export async function fetchReplySuggestions(
  message: string,
  tone: string,
  explainabilityMode = false,
): Promise<ReplyResult> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

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
        user_style: 'calm',
        retrieval_debug: explainabilityMode,
      }),
    });

    if (!response.ok) {
      if (response.status >= 500) {
        throw new ApiClientError('Server is waking up...', 'UNAVAILABLE');
      }
      throw new ApiClientError('Could not generate replies', 'BAD_RESPONSE');
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
      throw new ApiClientError('Server is waking up...', 'TIMEOUT');
    }

    throw new ApiClientError('Could not generate replies', 'UNKNOWN');
  } finally {
    clearTimeout(timeout);
  }
}
