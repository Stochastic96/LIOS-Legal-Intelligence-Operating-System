/**
 * LIOS API client — all calls to the FastAPI backend.
 * Set BASE_URL to your Mac's LAN IP:  e.g. http://192.168.1.42:8000
 * Change it in the Brain screen settings.
 */

import AsyncStorage from "@react-native-async-storage/async-storage";

const DEFAULT_URL = "http://192.168.0.101:8000";
const URL_KEY = "lios_server_url";

export async function getServerUrl(): Promise<string> {
  const stored = await AsyncStorage.getItem(URL_KEY);
  return stored || DEFAULT_URL;
}

export async function setServerUrl(url: string): Promise<void> {
  await AsyncStorage.setItem(URL_KEY, url.replace(/\/$/, ""));
}

async function get<T>(path: string): Promise<T> {
  const base = await getServerUrl();
  const res = await fetch(`${base}${path}`);
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const base = await getServerUrl();
  const res = await fetch(`${base}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json();
}

async function del<T>(path: string): Promise<T> {
  const base = await getServerUrl();
  const res = await fetch(`${base}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`DELETE ${path} → ${res.status}`);
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
};
