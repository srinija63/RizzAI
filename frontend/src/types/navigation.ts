export type RetrievalDebugItem = {
  pattern_id?: string | null;
  tone?: string | null;
  situation?: string | null;
  score?: number | null;
  reason?: string | null;
};

export type RankedReply = {
  text: string;
  label?: string;
  score?: number;
};

export type RootStackParamList = {
  Home: undefined;
  ChatInput: undefined;
  ReplyResults: {
    prompt: string;
    tone: string;
    suggestions: RankedReply[];
    retrievalDebug?: RetrievalDebugItem[];
    explainabilityMode?: boolean;
    note?: string | null;
    providerUsed?: string | null;
    latencyMs?: number | null;
    warning?: string | null;
  };
};
