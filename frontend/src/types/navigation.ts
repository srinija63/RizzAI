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

/** How forward / assertive generated replies should read (server: confidence_level). */
export type ConfidenceLevel = 'low' | 'medium' | 'high';

export type RootStackParamList = {
  HeroIntro: undefined;
  Home: undefined;
  ReplySetup: undefined;
  ChatInput: {
    tone: string;
    confidenceLevel: ConfidenceLevel;
  };
  ReplyResults: {
    prompt: string;
    tone: string;
    confidenceLevel?: ConfidenceLevel;
    suggestions: RankedReply[];
    retrievalDebug?: RetrievalDebugItem[];
    explainabilityMode?: boolean;
    note?: string | null;
    providerUsed?: string | null;
    latencyMs?: number | null;
    warning?: string | null;
  };
  OpenerGenerator: undefined;
  BioWriter: undefined;
  TextResults: {
    title: string;
    items: string[];
    subtitle?: string | null;
    providerUsed?: string | null;
  };
};
