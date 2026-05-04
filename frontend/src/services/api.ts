const API_BASE_URL = 'http://127.0.0.1:8000';

type RetrievalDebugItem = {
  pattern_id?: string | null;
  tone?: string | null;
  situation?: string | null;
  score?: number | null;
  reason?: string | null;
};

type ReplyApiResponse = {
  replies?: string[];
  suggestions: string[];
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
      message,
      tone,
      retrieval_debug: explainabilityMode,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Request failed');
  }

  const data = (await response.json()) as ReplyApiResponse;
  return data;
}
