import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { api, LearnNext } from "../api/client";

const STATUS_ICON: Record<string, string> = {
  mastered: "🏆",
  functional: "✅",
  connected: "🧩",
  learning: "📖",
  seed: "🌱",
  unknown: "🔲",
};

const STATUS_COLOR: Record<string, string> = {
  mastered: "#22c55e",
  functional: "#6366f1",
  connected: "#3b82f6",
  learning: "#f59e0b",
  seed: "#94a3b8",
  unknown: "#475569",
};

export default function LearnScreen() {
  const [learnData, setLearnData] = useState<LearnNext | null>(null);
  const [answer, setAnswer] = useState("");
  const [reference, setReference] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [overallPct, setOverallPct] = useState(0);
  const [result, setResult] = useState<{ name: string; pct: number; status: string; nextTopic: string | null } | null>(null);

  const loadNext = useCallback(async () => {
    setLoading(true);
    setResult(null);
    setAnswer("");
    setReference("");
    try {
      const data = await api.learn.next();
      setLearnData(data);
      const map = await api.learn.map();
      setOverallPct(map.overall_pct);
    } catch {
      setLearnData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadNext(); }, [loadNext]);

  const submitAnswer = useCallback(async () => {
    if (!learnData?.topic || !answer.trim()) return;
    setSubmitting(true);
    try {
      const res = await api.learn.answer(learnData.topic.id, answer.trim(), reference.trim());
      setResult({
        name: res.topic_updated.name,
        pct: res.topic_updated.pct,
        status: res.topic_updated.status,
        nextTopic: res.next_topic,
      });
      setOverallPct(res.overall_pct);
    } catch {
      // ignore
    } finally {
      setSubmitting(false);
    }
  }, [learnData, answer, reference]);

  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={["top"]}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#6366f1" />
          <Text style={styles.loadingText}>LIOS is deciding what to ask you…</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!learnData || learnData.all_mastered) {
    return (
      <SafeAreaView style={styles.container} edges={["top"]}>
        <View style={styles.center}>
          <Text style={styles.masteredEmoji}>🏆</Text>
          <Text style={styles.masteredTitle}>All topics mastered!</Text>
          <Text style={styles.masteredSub}>LIOS has learned everything in the current knowledge map.</Text>
        </View>
      </SafeAreaView>
    );
  }

  const topic = learnData.topic!;

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Learn Mode</Text>
        <View style={styles.progressBadge}>
          <Text style={styles.progressText}>{overallPct}% mapped</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        {/* Topic chip */}
        <View style={styles.topicRow}>
          <Text style={styles.topicIcon}>{STATUS_ICON[topic.status] ?? "📖"}</Text>
          <View>
            <Text style={[styles.topicName, { color: STATUS_COLOR[topic.status] ?? "#e2e8f0" }]}>
              {topic.name}
            </Text>
            <Text style={styles.topicCategory}>{topic.category}</Text>
          </View>
          <View style={styles.topicPct}>
            <Text style={styles.topicPctText}>{topic.pct}%</Text>
          </View>
        </View>

        {/* Progress bar */}
        <View style={styles.progressBar}>
          <View style={[styles.progressFill, { width: `${topic.pct}%` as any, backgroundColor: STATUS_COLOR[topic.status] }]} />
        </View>

        {/* Question card */}
        <View style={styles.questionCard}>
          <Text style={styles.questionLabel}>LIOS wants to know:</Text>
          <Text style={styles.questionText}>{learnData.question}</Text>
        </View>

        {result ? (
          /* After submitting */
          <View style={styles.resultCard}>
            <Text style={styles.resultTitle}>Stored ✓</Text>
            <Text style={styles.resultLine}>
              {result.name}: {result.pct}% ({result.status})
            </Text>
            {result.nextTopic && (
              <Text style={styles.resultNext}>Next topic: {result.nextTopic}</Text>
            )}
            <Pressable style={styles.nextBtn} onPress={loadNext}>
              <Text style={styles.nextBtnText}>Next Question →</Text>
            </Pressable>
          </View>
        ) : (
          /* Answer form */
          <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined}>
            <Text style={styles.label}>Your answer</Text>
            <TextInput
              style={styles.answerInput}
              value={answer}
              onChangeText={setAnswer}
              placeholder="Explain what you know…"
              placeholderTextColor="#475569"
              multiline
              textAlignVertical="top"
            />
            <Text style={styles.label}>Reference (optional)</Text>
            <TextInput
              style={styles.refInput}
              value={reference}
              onChangeText={setReference}
              placeholder="e.g. EUR-Lex, IFRS Foundation, ESMA"
              placeholderTextColor="#475569"
            />
            <View style={styles.actionRow}>
              <Pressable style={styles.skipBtn} onPress={loadNext}>
                <Text style={styles.skipBtnText}>Skip</Text>
              </Pressable>
              <Pressable
                style={[styles.teachBtn, !answer.trim() && styles.btnDisabled]}
                onPress={submitAnswer}
                disabled={!answer.trim() || submitting}
              >
                {submitting ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Text style={styles.teachBtnText}>Teach LIOS ↑</Text>
                )}
              </Pressable>
            </View>
          </KeyboardAvoidingView>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 32 },
  loadingText: { color: "#64748b", marginTop: 12, fontSize: 14 },
  masteredEmoji: { fontSize: 56, marginBottom: 16 },
  masteredTitle: { fontSize: 22, fontWeight: "700", color: "#e2e8f0", marginBottom: 8 },
  masteredSub: { fontSize: 14, color: "#64748b", textAlign: "center" },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "#1e293b" },
  headerTitle: { fontSize: 20, fontWeight: "700", color: "#e2e8f0" },
  progressBadge: { backgroundColor: "#1e293b", borderRadius: 20, paddingHorizontal: 12, paddingVertical: 4 },
  progressText: { fontSize: 12, fontWeight: "600", color: "#6366f1" },
  scroll: { padding: 16 },
  topicRow: { flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 12 },
  topicIcon: { fontSize: 28 },
  topicName: { fontSize: 17, fontWeight: "700" },
  topicCategory: { fontSize: 12, color: "#64748b", marginTop: 2 },
  topicPct: { marginLeft: "auto", backgroundColor: "#1e293b", borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4 },
  topicPctText: { color: "#e2e8f0", fontWeight: "700", fontSize: 14 },
  progressBar: { height: 6, backgroundColor: "#1e293b", borderRadius: 3, marginBottom: 20, overflow: "hidden" },
  progressFill: { height: "100%", borderRadius: 3 },
  questionCard: { backgroundColor: "#1e293b", borderRadius: 16, padding: 20, marginBottom: 20, borderLeftWidth: 4, borderLeftColor: "#6366f1" },
  questionLabel: { fontSize: 11, fontWeight: "600", color: "#6366f1", letterSpacing: 1, textTransform: "uppercase", marginBottom: 10 },
  questionText: { fontSize: 16, color: "#e2e8f0", lineHeight: 24 },
  label: { fontSize: 12, fontWeight: "600", color: "#64748b", marginBottom: 6, textTransform: "uppercase", letterSpacing: 0.5 },
  answerInput: { backgroundColor: "#1e293b", borderRadius: 12, padding: 14, color: "#e2e8f0", fontSize: 15, minHeight: 110, marginBottom: 14 },
  refInput: { backgroundColor: "#1e293b", borderRadius: 12, padding: 14, color: "#e2e8f0", fontSize: 15, marginBottom: 20 },
  actionRow: { flexDirection: "row", gap: 12 },
  skipBtn: { flex: 1, padding: 14, borderRadius: 12, backgroundColor: "#1e293b", alignItems: "center" },
  skipBtnText: { color: "#64748b", fontWeight: "600" },
  teachBtn: { flex: 2, padding: 14, borderRadius: 12, backgroundColor: "#6366f1", alignItems: "center" },
  btnDisabled: { opacity: 0.4 },
  teachBtnText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  resultCard: { backgroundColor: "#14532d", borderRadius: 16, padding: 20 },
  resultTitle: { fontSize: 18, fontWeight: "700", color: "#22c55e", marginBottom: 8 },
  resultLine: { fontSize: 15, color: "#e2e8f0", marginBottom: 4 },
  resultNext: { fontSize: 13, color: "#86efac", marginBottom: 16 },
  nextBtn: { backgroundColor: "#166534", borderRadius: 12, padding: 14, alignItems: "center" },
  nextBtnText: { color: "#22c55e", fontWeight: "700" },
});
