/**
 * LIOS API client — all calls to the FastAPI backend.
 * Server URL is persisted in AsyncStorage via URL_KEY.
 * If no value is stored yet, localhost is used (browser/simulator default).
 * For iPhone, set System → Server-Adresse to http://<mac-lan-ip>:8000.
 */

import AsyncStorage from "@react-native-async-storage/async-storage";

const DEFAULT_URL = "http://localhost:8000";
const URL_KEY = "lios_server_url";
const API_KEY_KEY = "lios_api_key";

export async function getServerUrl(): Promise<string> {
  const stored = await AsyncStorage.getItem(URL_KEY);
  return stored || DEFAULT_URL;
}

export async function setServerUrl(url: string): Promise<void> {
  await AsyncStorage.setItem(URL_KEY, url.trim().replace(/\/$/, ""));
}

export async function getApiKey(): Promise<string> {
  return (await AsyncStorage.getItem(API_KEY_KEY)) || "";
}

export async function setApiKey(apiKey: string): Promise<void> {
  const normalized = apiKey.trim();
  if (!normalized) {
    await AsyncStorage.removeItem(API_KEY_KEY);
    return;
  }
  await AsyncStorage.setItem(API_KEY_KEY, normalized);
}

async function buildHeaders(extra: Record<string, string> = {}): Promise<Record<string, string>> {
  const apiKey = await getApiKey();
  return {
    ...extra,
    ...(apiKey ? { "X-API-Key": apiKey } : {}),
  };
}

async function parseError(res: Response, method: string, path: string): Promise<never> {
  const text = await res.text().catch(() => "");
  const detail = text || `${res.status}`;
  throw new Error(`${method} ${path} -> ${res.status}${detail ? `: ${detail}` : ""}`);
}

async function get<T>(path: string): Promise<T> {
  const base = await getServerUrl();
  const res = await fetch(`${base}${path}`, { headers: await buildHeaders() });
  if (!res.ok) return parseError(res, "GET", path);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const base = await getServerUrl();
  const res = await fetch(`${base}${path}`, {
    method: "POST",
    headers: await buildHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  if (!res.ok) return parseError(res, "POST", path);
  return res.json();
}

async function del<T>(path: string): Promise<T> {
  const base = await getServerUrl();
  const res = await fetch(`${base}${path}`, {
    method: "DELETE",
    headers: await buildHeaders(),
  });
  if (!res.ok) return parseError(res, "DELETE", path);
  return res.json();
}

async function postForm<T>(path: string, form: FormData): Promise<T> {
  const base = await getServerUrl();
  const res = await fetch(`${base}${path}`, {
    method: "POST",
    headers: await buildHeaders(),
    body: form,
  });
  if (!res.ok) return parseError(res, "UPLOAD", path);
  return res.json();
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface BrainStatus {
  brain_on: boolean;
  model: string;
  base_url: string;
  llm_reachable: boolean;
  knowledge_chunks: number;
  active_rules: number;
  total_corrections: number;
  toggled_at: string | null;
}

export interface ChatResponse {
  message_id: string;
  answer: string;
  confidence: "high" | "medium" | "low";
  source: string;
  brain_used: boolean;
}

export interface FeedbackPayload {
  session_id: string;
  message_id: string;
  query: string;
  original_answer: string;
  feedback_type: "good" | "wrong" | "partial";
  correction_text?: string;
  make_rule?: boolean;
}

export interface Rule {
  id: string;
  created_at: string;
  source: string;
  topic: string;
  rule_text: string;
  active: boolean;
}

export interface Correction {
  id: string;
  created_at: string;
  session_id: string;
  user_query: string;
  feedback_type: string;
  correction_text: string;
  made_rule: boolean;
}

export interface LearnNext {
  all_mastered: boolean;
  topic: {
    id: string;
    name: string;
    category: string;
    status: string;
    pct: number;
    description: string;
  } | null;
  question: string | null;
}

export interface KnowledgeMapTopic {
  id: string;
  name: string;
  status: string;
  pct: number;
  last_updated: string | null;
}

export interface KnowledgeMap {
  overall_pct: number;
  total_topics: number;
  mastered: number;
  functional: number;
  learning: number;
  unknown: number;
  categories: Record<string, KnowledgeMapTopic[]>;
}

export type LLMMode = "local" | "groq" | "azure";

// ── Intelligence types ────────────────────────────────────────────────────────

export interface IntelligenceStats {
  total_chunks: number;
  total_regulations: number;
  total_official_docs: number;
  consumed_files: number;
  total_topics: number;
  total_questions_in_bank: number;
  total_answers_submitted: number;
  valid_answers: number;
  topics_functional_or_mastered: number;
  overall_learning_pct: number;
  corrections_count: number;
  answers_last_7_days: number;
  target_chunks: number;
  target_questions: number;
  corpus_completeness_pct: number;
}

export interface CorpusRegulation {
  regulation: string;
  celex_id: string;
  jurisdiction: string;
  chunk_count: number;
  article_count: number;
  articles: string[];
  source_url: string;
  last_indexed: string;
  published_date: string;
}

export interface TopicCoverage {
  id: string;
  name: string;
  category: string;
  status: string;
  pct: number;
  questions_in_bank: number;
  questions_asked: number;
  questions_answered: number;
  last_activity: string | null;
  has_corpus_chunks: boolean;
  corpus_chunk_count: number;
}

export interface AnswerRecord {
  id: string;
  ts: string;
  topic_name: string;
  category: string;
  question: string;
  user_answer: string;
  reference: string;
  pct_before: number;
  pct_after: number;
  valid: boolean;
  corpus_hint: string;
}

export interface CorpusFileRecord {
  filename: string;
  regulation: string;
  chunk_count: number;
  article_count: number;
  source_url: string;
  last_indexed: string;
  published_date: string;
}

export interface LLMModeStatus {
  mode: LLMMode;
  provider: string;
  model: string;
  label: string;
  reachable: boolean;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export const api = {
  health: () => get<{ status: string }>("/health"),

  brain: {
    status: () => get<BrainStatus>("/brain/status"),
    toggle: (enabled: boolean) => post<BrainStatus>("/brain/toggle", { enabled }),
  },

  chat: {
    send: (query: string, session_id: string, messages?: { role: string; content: string }[]) =>
      post<ChatResponse>("/chat", { query, session_id, messages }),
    history: (session_id: string) =>
      get<{ session_id: string; turns: unknown[] }>(`/chat/history/${session_id}`),
  },

  feedback: {
    submit: (payload: FeedbackPayload) => post<{ stored: boolean; rule_created: boolean; message: string }>("/feedback", payload),
  },

  memory: {
    corrections: (limit = 50) => get<{ corrections: Correction[]; total: number }>(`/memory/corrections?limit=${limit}`),
    rules: () => get<{ rules: Rule[]; total: number }>("/memory/rules"),
    addRule: (rule_text: string, topic = "general") => post<{ created: boolean; rule: Rule }>("/memory/rules", { rule_text, topic }),
    deleteRule: (id: string) => del<{ deactivated: boolean }>(`/memory/rules/${id}`),
  },

  learn: {
    next: () => get<LearnNext>("/learn/next"),
    answer: (topic_id: string, answer_text: string, reference = "") =>
      post<{ topic_updated: KnowledgeMapTopic; overall_pct: number; next_topic: string | null }>(
        "/learn/answer",
        { topic_id, answer_text, reference }
      ),
    map: () => get<KnowledgeMap>("/learn/map"),
  },

  llmMode: {
    get: () => get<LLMModeStatus>("/api/llm-mode"),
    set: (mode: LLMMode, api_key?: string) =>
      post<{ mode: LLMMode; label: string; model: string }>("/api/llm-mode", { mode, api_key }),
  },

  stats: {
    tokenUsage: () => get<{
      total_calls: number;
      total_tokens: number;
      total_cost_usd: number;
      by_model: Record<string, { calls: number; tokens: number; cost_usd: number }>;
    }>("/api/token-usage"),
    exportTraining: (limit = 500) =>
      get<{ samples: number; jsonl: string }>(`/api/training-export?limit=${limit}`),
  },

  upload: {
    document: (form: FormData) =>
      postForm<{ status: string; chunks_added: number; filename: string }>("/api/upload", form),
    corrections: (limit = 100) =>
      get<{ corrections: Correction[]; total: number }>(`/memory/corrections?limit=${limit}`),
  },

  intelligence: {
    stats:   () => get<IntelligenceStats>("/intelligence/stats"),
    corpus:  () => get<CorpusRegulation[]>("/intelligence/corpus"),
    topics:  () => get<TopicCoverage[]>("/intelligence/topics"),
    answers: (limit = 20) =>
      get<{ answers: AnswerRecord[]; total: number }>(`/intelligence/answers?limit=${limit}`),
    files: (query = "", limit = 50) =>
      get<{ files: CorpusFileRecord[]; total: number; query: string }>(
        `/intelligence/files?query=${encodeURIComponent(query)}&limit=${limit}`
      ),
  },
};
