export type RootStackParamList = {
  Home: undefined;
  ChatInput: undefined;
  ReplyResults: {
    prompt: string;
    tone: string;
    suggestions: string[];
    retrievalDebug?: {
      pattern_id?: string | null;
      tone?: string | null;
      situation?: string | null;
      score?: number | null;
      reason?: string | null;
    }[];
    explainabilityMode?: boolean;
    note?: string | null;
  };
};
