import { Platform } from 'react-native';

// Backend URL configuration:
// - Web (browser on your laptop): keep localhost.
// - Mobile (Expo Go on phone): set this to your laptop's LAN IP.
const MOBILE_LAN_API_BASE_URL = 'http://192.168.0.100:8000';
const WEB_LOCALHOST_API_BASE_URL = 'http://127.0.0.1:8000';

const API_BASE_URL =
  Platform.OS === 'web' ? WEB_LOCALHOST_API_BASE_URL : MOBILE_LAN_API_BASE_URL;

type RetrievalDebugItem = {
  pattern_id?: string | null;
  tone?: string | null;
  situation?: string | null;
  score?: number | null;
  reason?: string | null;
};

type ReplyApiResponse = {
  replies?: Array<string | { text?: string }>;
  suggestions?: string[];
  labels?: string[];
  note?: string | null;
  retrieval_debug?: RetrievalDebugItem[] | null;
};

export async function fetchReplySuggestions(
  message: string,
  tone: string,
  explainabilityMode = false
) {
  const response = await fetch(`${API_BASE_URL}/api/reply`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      conversation_text: message,
      tone,
      retrieval_debug: explainabilityMode,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Request failed');
  }

  const data = (await response.json()) as ReplyApiResponse;
  const replyTexts =
    data.replies?.map((reply) =>
      typeof reply === 'string' ? reply : (reply.text ?? '').trim()
    ).filter(Boolean) ??
    data.suggestions ??
    [];

  return {
    ...data,
    replies: replyTexts,
    suggestions: replyTexts,
  };
}
