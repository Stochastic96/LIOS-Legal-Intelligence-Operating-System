import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { api, LearnNext } from "../api/client";
import AnimatedProgressBar from "../components/AnimatedProgressBar";
import Card from "../components/Card";
import ScalePressable from "../components/ScalePressable";
import { C, F, R, S, W } from "../theme";

const STATUS_ICON: Record<string, string> = {
  mastered:   "🏆",
  functional: "✅",
  connected:  "🧩",
  learning:   "📖",
  seed:       "🌱",
  unknown:    "🔲",
};

const STATUS_COLOR: Record<string, string> = {
  mastered:   C.green,
  functional: C.accent,
  connected:  C.accent,
  learning:   C.amber,
  seed:       C.mid,
  unknown:    C.dim,
};

export default function LearnScreen() {
  const [learnData, setLearnData] = useState<LearnNext | null>(null);
  const [answer, setAnswer] = useState("");
  const [reference, setReference] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [overallPct, setOverallPct] = useState(0);
  const [streak, setStreak] = useState(0);
  const [answerFocused, setAnswerFocused] = useState(false);
  const [result, setResult] = useState<{
    name: string;
    pct: number;
    status: string;
    nextTopic: string | null;
  } | null>(null);

  const mountAnim  = useRef(new Animated.Value(0)).current;
  const streakAnim = useRef(new Animated.Value(1)).current;
  const prevStreak = useRef(streak);

  useEffect(() => {
    Animated.timing(mountAnim, {
      toValue: 1,
      duration: 320,
      useNativeDriver: true,
    }).start();
  }, []);

  useEffect(() => {
    if (streak > prevStreak.current) {
      Animated.sequence([
        Animated.timing(streakAnim, { toValue: 1.35, duration: 120, useNativeDriver: true }),
        Animated.spring(streakAnim, { toValue: 1, speed: 20, bounciness: 8, useNativeDriver: true }),
      ]).start();
    }
    prevStreak.current = streak;
  }, [streak]);

  const loadNext = useCallback(async (resetStreak = false) => {
    setLoading(true);
    setResult(null);
    setAnswer("");
    setReference("");
    if (resetStreak) setStreak(0);
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

  useEffect(() => {
    loadNext(false);
  }, [loadNext]);

  const submitAnswer = useCallback(async () => {
    if (!learnData?.topic || !answer.trim()) return;
    setSubmitting(true);
    try {
      const res = await api.learn.answer(learnData.topic.id, answer.trim(), reference.trim());
      setStreak((s) => s + 1);
      setResult({
        name:      res.topic_updated.name,
        pct:       res.topic_updated.pct,
        status:    res.topic_updated.status,
        nextTopic: res.next_topic,
      });
      setOverallPct(res.overall_pct);
    } catch {
      // ignore
    } finally {
      setSubmitting(false);
    }
  }, [learnData, answer, reference]);

  const fadeStyle = {
    opacity: mountAnim,
    transform: [
      {
        translateY: mountAnim.interpolate({
          inputRange: [0, 1],
          outputRange: [16, 0],
        }),
      },
    ],
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={["top"]}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={C.accent} />
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
          <Text style={styles.masteredSub}>
            LIOS has learned everything in the current knowledge map.
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  const topic = learnData.topic!;
  const topicStatusColor = STATUS_COLOR[topic.status] ?? C.accent;

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Learn Mode</Text>
        <View style={styles.headerRight}>
          {streak > 0 && (
            <Animated.View
              style={[styles.streakBadge, { transform: [{ scale: streakAnim }] }]}
            >
              <Text style={styles.streakText}>🔥 {streak}</Text>
            </Animated.View>
          )}
          <View style={styles.progressBadge}>
            <Text style={styles.progressText}>{overallPct}% mapped</Text>
          </View>
        </View>
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        keyboardShouldPersistTaps="handled"
      >
        <Animated.View style={fadeStyle}>
          {/* Topic chip */}
          <Card surface="s2" style={[styles.topicChip, { borderLeftColor: topicStatusColor }]}>
            <View style={styles.topicRow}>
              <Text style={styles.topicIcon}>{STATUS_ICON[topic.status] ?? "📖"}</Text>
              <View style={styles.topicMeta}>
                <Text style={[styles.topicName, { color: topicStatusColor }]}>
                  {topic.name}
                </Text>
                <Text style={styles.topicCategory}>{topic.category}</Text>
              </View>
              <View style={styles.topicPctBadge}>
                <Text style={[styles.topicPctText, { color: topicStatusColor }]}>
                  {topic.pct}%
                </Text>
              </View>
            </View>
            <AnimatedProgressBar
              value={topic.pct}
              color={topicStatusColor}
              height={4}
              bgColor={C.s1}
              duration={600}
            />
          </Card>

          {/* Question card */}
          <Card surface="s2" style={styles.questionCard}>
            <Text style={styles.questionLabel}>LIOS wants to know</Text>
            <Text style={styles.questionText}>{learnData.question}</Text>
          </Card>

          {result ? (
            /* Result card */
            <View style={styles.resultCard}>
              <View style={styles.resultHeader}>
                <Feather name="check-circle" size={22} color={C.green} />
                <Text style={styles.resultTitle}>Stored</Text>
              </View>
              <Text style={styles.resultLine}>
                {result.name}: {result.pct}% ({result.status})
              </Text>

              {result.nextTopic && (
                <View style={styles.nextTopicRow}>
                  <View style={styles.nextTopicLabelRow}>
                    <Feather name="arrow-right" size={11} color={C.accent} />
                    <Text style={styles.nextTopicLabel}>UP NEXT</Text>
                  </View>
                  <Text style={styles.resultNext}>{result.nextTopic}</Text>
                </View>
              )}

              <ScalePressable onPress={() => loadNext(false)}>
                <View style={styles.nextBtn}>
                  <Text style={styles.nextBtnText}>Next Question</Text>
                  <Feather name="chevron-right" size={16} color={C.accent} />
                </View>
              </ScalePressable>
            </View>
          ) : (
            /* Answer form */
            <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined}>
              <Text style={styles.fieldLabel}>Your answer</Text>
              <TextInput
                style={[
                  styles.answerInput,
                  answerFocused && styles.inputFocused,
                ]}
                value={answer}
                onChangeText={setAnswer}
                onFocus={() => setAnswerFocused(true)}
                onBlur={() => setAnswerFocused(false)}
                placeholder="Explain what you know…"
                placeholderTextColor={C.dim}
                multiline
                textAlignVertical="top"
              />
              <Text style={styles.fieldLabel}>Reference (optional)</Text>
              <TextInput
                style={styles.refInput}
                value={reference}
                onChangeText={setReference}
                placeholder="e.g. EUR-Lex, IFRS Foundation, ESMA"
                placeholderTextColor={C.dim}
              />

              <View style={styles.actionRow}>
                <ScalePressable onPress={() => loadNext(true)} style={{ flex: 1 }}>
                  <View style={styles.skipBtn}>
                    <Feather name="skip-forward" size={15} color={C.mid} />
                    <Text style={styles.skipBtnText}>Skip</Text>
                  </View>
                </ScalePressable>

                <ScalePressable
                  onPress={submitAnswer}
                  disabled={!answer.trim() || submitting}
                  style={{ flex: 2 }}
                >
                  <View style={[styles.teachBtn, (!answer.trim() || submitting) && styles.btnDisabled]}>
                    {submitting ? (
                      <ActivityIndicator size="small" color={C.bg} />
                    ) : (
                      <>
                        <Text style={styles.teachBtnText}>Teach LIOS</Text>
                        <Feather name="send" size={15} color={C.bg} />
                      </>
                    )}
                  </View>
                </ScalePressable>
              </View>
            </KeyboardAvoidingView>
          )}
        </Animated.View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container:      { flex: 1, backgroundColor: C.bg },
  center:         { flex: 1, alignItems: "center", justifyContent: "center", padding: S.xl },
  loadingText:    { color: C.mid, marginTop: S.sm, fontSize: F.sm },
  masteredEmoji:  { fontSize: 52, marginBottom: S.md },
  masteredTitle:  { fontSize: F.xl, fontWeight: W.bold, color: C.text, marginBottom: S.sm },
  masteredSub:    { fontSize: F.sm, color: C.mid, textAlign: "center" },

  header:         {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: S.md,
    paddingVertical: S.sm + 2,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
  },
  headerTitle:    { fontSize: F.lg, fontWeight: W.bold, color: C.text },
  headerRight:    { flexDirection: "row", alignItems: "center", gap: S.sm },
  streakBadge:    {
    backgroundColor: C.redDim,
    borderRadius: R.full,
    paddingHorizontal: S.sm + 2,
    paddingVertical: 3,
  },
  streakText:     { fontSize: F.xs, fontWeight: W.bold, color: C.amber },
  progressBadge:  {
    backgroundColor: C.accentDim,
    borderRadius: R.full,
    paddingHorizontal: S.sm + 4,
    paddingVertical: 3,
  },
  progressText:   { fontSize: F.xs, fontWeight: W.semi, color: C.accent },

  scroll:         { padding: S.md, paddingBottom: S.xxl },

  topicChip:      { marginBottom: S.md, borderLeftWidth: 3, gap: S.sm },
  topicRow:       { flexDirection: "row", alignItems: "center", gap: S.sm, marginBottom: S.sm },
  topicIcon:      { fontSize: 24 },
  topicMeta:      { flex: 1 },
  topicName:      { fontSize: F.md, fontWeight: W.bold },
  topicCategory:  { fontSize: F.xs, color: C.mid, marginTop: 2 },
  topicPctBadge:  {
    backgroundColor: C.s3,
    borderRadius: R.sm,
    paddingHorizontal: S.sm,
    paddingVertical: 3,
  },
  topicPctText:   { fontSize: F.sm, fontWeight: W.bold },

  questionCard:   { marginBottom: S.md, borderLeftWidth: 3, borderLeftColor: C.accent },
  questionLabel:  {
    fontSize: F.xs,
    fontWeight: W.bold,
    color: C.accent,
    letterSpacing: 1.2,
    textTransform: "uppercase",
    marginBottom: S.sm,
  },
  questionText:   { fontSize: F.md, color: C.text, lineHeight: F.md * 1.6 },

  fieldLabel:     {
    fontSize: F.xs,
    fontWeight: W.semi,
    color: C.mid,
    marginBottom: S.xs,
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  answerInput:    {
    backgroundColor: C.s2,
    borderRadius: R.sm,
    borderWidth: 1,
    borderColor: C.border,
    padding: S.sm + 4,
    color: C.text,
    fontSize: F.md,
    minHeight: 110,
    marginBottom: S.sm,
  },
  inputFocused:   { borderColor: C.borderBright },
  refInput:       {
    backgroundColor: C.s2,
    borderRadius: R.sm,
    borderWidth: 1,
    borderColor: C.border,
    padding: S.sm + 4,
    color: C.text,
    fontSize: F.sm,
    marginBottom: S.lg,
  },

  actionRow:      { flexDirection: "row", gap: S.sm },
  skipBtn:        {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: S.xs,
    padding: S.sm + 4,
    borderRadius: R.sm,
    backgroundColor: C.s2,
    borderWidth: 1,
    borderColor: C.border,
  },
  skipBtnText:    { color: C.mid, fontWeight: W.semi, fontSize: F.sm },
  teachBtn:       {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: S.xs,
    padding: S.sm + 4,
    borderRadius: R.sm,
    backgroundColor: C.accent,
  },
  btnDisabled:    { opacity: 0.35 },
  teachBtnText:   { color: C.bg, fontWeight: W.bold, fontSize: F.sm },

  resultCard:     {
    backgroundColor: C.greenDim,
    borderRadius: R.md,
    borderWidth: 1,
    borderColor: C.green,
    padding: S.md,
    gap: S.sm,
  },
  resultHeader:   { flexDirection: "row", alignItems: "center", gap: S.sm, marginBottom: S.xs },
  resultTitle:    { fontSize: F.lg, fontWeight: W.bold, color: C.green },
  resultLine:     { fontSize: F.sm, color: C.text },

  nextTopicRow:   {
    backgroundColor: C.accentDim,
    borderRadius: R.sm,
    padding: S.sm,
    borderWidth: 1,
    borderColor: C.border,
  },
  nextTopicLabelRow: { flexDirection: "row", alignItems: "center", gap: 4, marginBottom: 4 },
  nextTopicLabel: {
    fontSize: 10,
    fontWeight: W.bold,
    color: C.accent,
    letterSpacing: 1.4,
    textTransform: "uppercase",
  },
  resultNext:     { fontSize: F.sm, color: C.text, fontWeight: W.semi },

  nextBtn:        {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: S.xs,
    backgroundColor: C.accentDim,
    borderRadius: R.sm,
    borderWidth: 1,
    borderColor: C.accent,
    padding: S.sm + 4,
    marginTop: S.xs,
  },
  nextBtnText:    { color: C.accent, fontWeight: W.bold, fontSize: F.sm },
});
