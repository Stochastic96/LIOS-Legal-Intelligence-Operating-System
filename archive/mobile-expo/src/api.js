import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Default placeholders; Settings screen persists overrides in AsyncStorage.
export const DEFAULT_LIOS_BASE_URL = 'http://YOUR_MACHINE_IP:8000';
export const DEFAULT_API_KEY = '';

async function getConfig() {
  const base = (await AsyncStorage.getItem('LIOS_BASE_URL')) || DEFAULT_LIOS_BASE_URL;
  const key = (await AsyncStorage.getItem('LIOS_API_KEY')) || DEFAULT_API_KEY;
  return { base, key };
}

async function headers() {
  const { key } = await getConfig();
  const h = { 'Content-Type': 'application/json' };
  if (key) h['x-api-key'] = key;
  return h;
}

export async function postMessage(sessionId, query) {
  const { base } = await getConfig();
  const payload = { session_id: sessionId, query };
  const url = `${base.replace(/\/$/, '')}/chat/api/message`;
  const resp = await axios.post(url, payload, { headers: await headers() });
  return resp.data;
}

export async function getNextQuestion(sessionId) {
  const { base } = await getConfig();
  const url = `${base.replace(/\/$/, '')}/chat/api/next-question?session_id=${encodeURIComponent(
    sessionId,
  )}`;
  const resp = await axios.get(url, { headers: await headers() });
  return resp.data;
}

export async function submitFeedback(payload) {
  const { base } = await getConfig();
  const url = `${base.replace(/\/$/, '')}/chat/api/feedback`;
  const resp = await axios.post(url, payload, { headers: await headers() });
  return resp.data;
}
