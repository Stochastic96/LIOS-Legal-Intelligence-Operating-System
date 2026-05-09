import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { api, KnowledgeMap, KnowledgeMapTopic } from "../api/client";
import TypingIndicator from "../components/TypingIndicator";
import { C, F, R, S, W, pctColor, pctBgColor } from "../theme";

// ── Message model ──────────────────────────────────────────────────────────────

type LearnMsg =
  | { kind: "dashboard"; id: string; map: KnowledgeMap }
  | {
      kind: "question";
      id: string;
      topicId: string;
      topic: string;
      category: string;
      topicPct: number;
      topicStatus: string;
      text: string;
    }
  | { kind: "user"; id: string; text: string }
  | {
      kind: "result";
      id: string;
      newPct: number;
      status: string;
      nextTopic: string | null;
    }
  | { kind: "mastered"; id: string };

const STATUS_LABEL: Record<string, string> = {
  mastered:   "Beherrscht",
  functional: "Funktional",
  connected:  "Vernetzt",
  learning:   "In Bearbeitung",
  seed:       "Einführung",
  unknown:    "Unbekannt",
};

// ── Animated progress bar (inline, lightweight) ────────────────────────────────

function ProgressBar({ value, color, height = 4 }: { value: number; color: string; height?: number }) {
  const anim = useRef(new Animated.Value(value)).current;
  useEffect(() => {
    Animated.timing(anim, { toValue: value, duration: 500, useNativeDriver: false }).start();
  }, [value]);
  return (
    <View style={[st.pbTrack, { height }]}>
      <Animated.View
        style={[
          st.pbFill,
          { height, backgroundColor: color, width: anim.interpolate({ inputRange: [0, 100], outputRange: ["0%", "100%"] }) },
        ]}
      />
    </View>
  );
}

// ── Dashboard card (from KnowledgeMapScreen) ──────────────────────────────────

function DashboardCard({ map: m, readyPct, isReady, cats }: {
  map: KnowledgeMap;
  readyPct: number;
  isReady: boolean;
  cats: [string, KnowledgeMapTopic[]][];
}) {
  const [expanded, setExpanded] = React.useState<Record<string, boolean>>({});
  const toggle = (cat: string) => setExpanded((p) => ({ ...p, [cat]: !p[cat] }));

  return (
    <View style={st.dashCard}>
      <View style={st.dashAccent} />
      <View style={st.dashBody}>
        <View style={st.dashHeaderRow}>
          <View style={st.dashIconBox}>
            <Feather name="cpu" size={16} color={C.primary} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={st.dashTitle}>LIOS Wissensprofil</Text>
            <Text style={st.dashSub}>EU-Recht · EuGH-Rechtsprechung · Deutsches Recht</Text>
          </View>
          <View style={[st.readyBadge, { backgroundColor: isReady ? C.greenBg : C.amberBg }]}>
            <Text style={[st.readyText, { color: isReady ? C.green : C.amber }]}>
              {isReady ? "Mandatsbereit" : "In Ausbildung"}
            </Text>
          </View>
        </View>

        {/* Overall progress bar */}
        <View style={st.dashOverallRow}>
          <Text style={st.dashPctLarge}>{readyPct}%</Text>
          <View style={{ flex: 1 }}>
            <ProgressBar value={readyPct} color={pctColor(readyPct)} height={8} />
          </View>
        </View>

        {/* Stat tiles */}
        <View style={st.statRow}>
          {[
            { label: "Beherrscht", count: m.mastered,   color: C.green,   bg: C.greenBg },
            { label: "Funktional", count: m.functional, color: C.primary, bg: C.primaryDim },
            { label: "In Bearb.",  count: m.learning,   color: C.amber,   bg: C.amberBg },
            { label: "Unbekannt",  count: m.unknown,    color: C.dim,     bg: C.s2 },
          ].map(({ label, count, color, bg }) => (
            <View key={label} style={[st.statTile, { backgroundColor: bg }]}>
              <Text style={[st.statCount, { color }]}>{count}</Text>
              <Text style={[st.statLabel, { color }]}>{label}</Text>
            </View>
          ))}
        </View>

        <View style={st.dashDivider} />

        {/* Category sections — expandable */}
        {cats.map(([cat, topics]) => {
          const catPct = Math.round(topics.reduce((s, t) => s + (t as any).pct, 0) / topics.length);
          const open   = !!expanded[cat];
          return (
            <View key={cat}>
              <TouchableOpacity style={st.catHeaderRow} onPress={() => toggle(cat)} activeOpacity={0.7}>
                <View style={st.dashCatBar}>
                  <Text style={st.dashCatName} numberOfLines={1}>{cat}</Text>
                  <ProgressBar value={catPct} color={pctColor(catPct)} height={4} />
                </View>
                <Text style={[st.dashCatPct, { color: pctColor(catPct) }]}>{catPct}%</Text>
                <Feather name={open ? "chevron-up" : "chevron-down"} size={13} color={C.dim} />
              </TouchableOpacity>
              {open && topics.map((t) => (
                <View key={t.id} style={st.topicRow}>
                  <View style={[st.topicDot, { backgroundColor: pctColor(t.pct) }]} />
                  <Text style={st.topicRowName} numberOfLines={1}>{t.name}</Text>
                  <View style={st.topicBarWrap}>
                    <ProgressBar value={t.pct} color={pctColor(t.pct)} height={3} />
                  </View>
                  <View style={[st.topicStatusBadge, { backgroundColor: pctBgColor(t.pct) }]}>
                    <Text style={[st.topicStatusText, { color: pctColor(t.pct) }]}>
                      {STATUS_LABEL[t.status] ?? t.status}
                    </Text>
                  </View>
                </View>
              ))}
            </View>
          );
        })}
      </View>
    </View>
  );
}

// ── Main screen ────────────────────────────────────────────────────────────────

export default function LearnScreen() {
  const [messages, setMessages]     = useState<LearnMsg[]>([]);
  const [answer, setAnswer]         = useState("");
  const [refText, setRefText]       = useState("");
  const [showRef, setShowRef]       = useState(false);
  const [loading, setLoading]       = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [awaitingNext, setAwaitingNext] = useState(false); // result shown, waiting for Weiter
  const [overallPct, setOverallPct] = useState(0);
  const [streak, setStreak]         = useState(0);
  const [inputFocused, setInputFocused] = useState(false);
  const [currentTopicId, setCurrentTopicId] = useState<string | null>(null);

  const listRef = useRef<FlatList>(null);

  const toBottom = useCallback(() => {
    setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 60);
  }, []);

  const pushMsg = useCallback((msg: LearnMsg) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  const loadNext = useCallback(async () => {
    setLoading(true);
    setAnswer("");
    setRefText("");
    setShowRef(false);
    setAwaitingNext(false);
    try {
      const data = await api.learn.next();
      if (data.all_mastered || !data.topic || !data.question) {
        pushMsg({ kind: "mastered", id: `m${Date.now()}` });
      } else {
        setCurrentTopicId(data.topic.id);
        setOverallPct((p) => data.topic ? data.topic.pct : p);
        pushMsg({
          kind:        "question",
          id:          `q${Date.now()}`,
          topicId:     data.topic.id,
          topic:       data.topic.name,
          category:    data.topic.category,
          topicPct:    data.topic.pct,
          topicStatus: data.topic.status,
          text:        data.question,
        });
      }
    } catch {
      pushMsg({
        kind: "result", id: `err${Date.now()}`,
        newPct: 0, status: "unknown", nextTopic: null,
      });
    } finally {
      setLoading(false);
    }
  }, [pushMsg]);

  useEffect(() => {
    (async () => {
      const map = await api.learn.map().catch(() => null);
      if (map) pushMsg({ kind: "dashboard", id: "dash", map });
      await loadNext();
    })();
  }, [loadNext, pushMsg]);

  const submitAnswer = useCallback(async () => {
    if (!answer.trim() || submitting || awaitingNext || !currentTopicId) return;
    const text = answer.trim();
    const ref  = refText.trim();
    pushMsg({ kind: "user", id: `u${Date.now()}`, text });
    setAnswer("");
    setRefText("");
    setShowRef(false);
    setSubmitting(true);
    try {
      const res = await api.learn.answer(currentTopicId, text, ref);
      setOverallPct(res.overall_pct);
      setStreak((s) => s + 1);
      pushMsg({
        kind:      "result",
        id:        `r${Date.now()}`,
        newPct:    res.topic_updated.pct,
        status:    res.topic_updated.status,
        nextTopic: res.next_topic,
      });
      setAwaitingNext(true);
    } catch {
      pushMsg({ kind: "result", id: `err${Date.now()}`, newPct: 0, status: "error", nextTopic: null });
    } finally {
      setSubmitting(false);
    }
  }, [answer, refText, submitting, awaitingNext, currentTopicId, pushMsg]);

  // ── Render a single message ─────────────────────────────────────────────────

  const renderItem = ({ item }: { item: LearnMsg }) => {
    if (item.kind === "dashboard") {
      const m = item.map;
      const readyPct = m.overall_pct;
      const isReady  = readyPct >= 70;
      const cats = Object.entries(m.categories);
      return (
        <DashboardCard
          map={m}
          readyPct={readyPct}
          isReady={isReady}
          cats={cats}
        />
      );
    }

    if (item.kind === "question") {
      return (
        <View style={st.questionCard}>
          <View style={st.questionAccent} />
          <View style={st.questionBody}>
            <View style={st.questionMeta}>
              <View style={st.fragenLabel}>
                <Feather name="help-circle" size={11} color={C.primary} />
                <Text style={st.fragenText}>FRAGE</Text>
              </View>
              <View style={st.catPill}>
                <Text style={st.catText}>{item.category}</Text>
              </View>
            </View>
            <Text style={st.topicName}>{item.topic}</Text>
            <View style={st.topicPctRow}>
              <ProgressBar value={item.topicPct} color={pctColor(item.topicPct)} height={4} />
              <Text style={[st.topicPctText, { color: pctColor(item.topicPct) }]}>{item.topicPct}%</Text>
            </View>
            <View style={st.qDivider} />
            <Text style={st.questionText}>{item.text}</Text>
          </View>
        </View>
      );
    }

    if (item.kind === "user") {
      return (
        <View style={st.userRow}>
          <View style={st.userBubble}>
            <Text style={st.userText}>{item.text}</Text>
          </View>
        </View>
      );
    }

    if (item.kind === "result") {
      if (item.status === "error") {
        return (
          <View style={st.errorBubble}>
            <Feather name="alert-circle" size={14} color={C.red} />
            <Text style={st.errorText}>Verbindungsfehler — bitte erneut versuchen.</Text>
          </View>
        );
      }
      const col = pctColor(item.newPct);
      return (
        <View style={st.resultCard}>
          <View style={[st.resultAccent, { backgroundColor: col }]} />
          <View style={st.resultBody}>
            <View style={st.resultTop}>
              <View>
                <Text style={st.resultLabel}>ERGEBNIS</Text>
                <Text style={[st.resultStatus, { color: col }]}>
                  {STATUS_LABEL[item.status] ?? item.status}
                </Text>
              </View>
              <Text style={[st.resultPct, { color: col }]}>{item.newPct}%</Text>
            </View>
            <ProgressBar value={item.newPct} color={col} height={6} />
            {item.nextTopic && (
              <Text style={st.nextHint}>Nächstes: {item.nextTopic}</Text>
            )}
            <TouchableOpacity style={st.weiterBtn} onPress={loadNext} activeOpacity={0.75}>
              <Text style={st.weiterText}>Weiter</Text>
              <Feather name="arrow-right" size={14} color={C.card} />
            </TouchableOpacity>
          </View>
        </View>
      );
    }

    if (item.kind === "mastered") {
      return (
        <View style={st.masteredCard}>
          <View style={[st.masteredIcon]}>
            <Feather name="award" size={28} color={C.green} />
          </View>
          <Text style={st.masteredTitle}>Alle Themen beherrscht!</Text>
          <Text style={st.masteredSub}>Sie haben alle EU-Compliance-Themen abgeschlossen.</Text>
          <TouchableOpacity style={st.weiterBtn} onPress={loadNext} activeOpacity={0.75}>
            <Feather name="refresh-cw" size={14} color={C.card} />
            <Text style={st.weiterText}>Neu starten</Text>
          </TouchableOpacity>
        </View>
      );
    }

    return null;
  };

  const canSend = answer.trim().length > 0 && !submitting && !awaitingNext && !loading;

  return (
    <SafeAreaView style={st.root} edges={["top"]}>
      {/* Header */}
      <View style={st.header}>
        <Text style={st.headerTitle}>Lernen</Text>
        <View style={st.headerRight}>
          {streak > 0 && (
            <View style={st.streakBadge}>
              <Feather name="zap" size={11} color={C.amber} />
              <Text style={st.streakText}>{streak}</Text>
            </View>
          )}
          <View style={st.pctBadge}>
            <Text style={st.pctText}>{overallPct}%</Text>
          </View>
        </View>
      </View>

      {/* Thin overall progress bar */}
      <ProgressBar value={overallPct} color={C.primary} height={3} />

      <KeyboardAvoidingView
        style={st.flex}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={Platform.OS === "ios" ? 56 : 0}
      >
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(m) => m.id}
          renderItem={renderItem}
          style={st.flex}
          contentContainerStyle={messages.length === 0 ? st.emptyContainer : st.listContent}
          keyboardShouldPersistTaps="handled"
          onContentSizeChange={toBottom}
          ListEmptyComponent={
            <View style={st.emptyState}>
              <View style={st.emptyIcon}>
                <Feather name="book-open" size={26} color={C.primary} />
              </View>
              <Text style={st.emptyTitle}>EU-Compliance Lernmodus</Text>
              <Text style={st.emptySub}>CSRD · ESRS · EU-Taxonomie · SFDR · DSGVO</Text>
            </View>
          }
        />

        {(loading || submitting) && <TypingIndicator />}

        {/* Input bar */}
        <View style={st.inputArea}>
          {showRef && (
            <TextInput
              style={st.refInput}
              value={refText}
              onChangeText={setRefText}
              placeholder="Quelle (z.B. CSRD Art. 19a) — optional"
              placeholderTextColor={C.dim}
            />
          )}
          <View style={st.inputRow}>
            <TouchableOpacity
              style={[st.refToggle, showRef && st.refToggleOn]}
              onPress={() => setShowRef((v) => !v)}
              activeOpacity={0.7}
            >
              <Feather name="link" size={14} color={showRef ? C.primary : C.dim} />
            </TouchableOpacity>
            <TextInput
              style={[st.input, inputFocused && st.inputFocused]}
              value={answer}
              onChangeText={setAnswer}
              onFocus={() => setInputFocused(true)}
              onBlur={() => setInputFocused(false)}
              placeholder={awaitingNext ? "Tippen Sie auf Weiter…" : "Ihre Antwort eingeben…"}
              placeholderTextColor={C.dim}
              multiline
              maxLength={800}
              editable={!awaitingNext && !loading}
            />
            <TouchableOpacity
              style={[st.sendBtn, !canSend && st.sendBtnOff]}
              onPress={submitAnswer}
              disabled={!canSend}
              activeOpacity={0.75}
            >
              <Feather name="send" size={15} color={canSend ? C.card : C.dim} />
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────

const st = StyleSheet.create({
  root:  { flex: 1, backgroundColor: C.bg },
  flex:  { flex: 1 },

  // Header
  header:      { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: S.md, paddingVertical: S.sm + 2, backgroundColor: C.card, borderBottomWidth: 1, borderBottomColor: C.border },
  headerTitle: { fontSize: F.xl, fontWeight: W.bold, color: C.text },
  headerRight: { flexDirection: "row", alignItems: "center", gap: S.sm },
  streakBadge: { flexDirection: "row", alignItems: "center", gap: 3, backgroundColor: C.amberBg, borderRadius: R.full, paddingHorizontal: S.sm, paddingVertical: 4, borderWidth: 1, borderColor: C.amber + "44" },
  streakText:  { fontSize: F.xs, fontWeight: W.bold, color: C.amber },
  pctBadge:    { backgroundColor: C.primaryDim, borderRadius: R.full, paddingHorizontal: S.sm, paddingVertical: 4 },
  pctText:     { fontSize: F.xs, fontWeight: W.bold, color: C.primary },

  // Progress bar
  pbTrack: { backgroundColor: C.border, borderRadius: 2, overflow: "hidden", width: "100%" },
  pbFill:  { borderRadius: 2 },

  // List
  listContent:    { paddingHorizontal: S.md, paddingVertical: S.md, gap: S.md },
  emptyContainer: { flex: 1 },
  emptyState:     { flex: 1, alignItems: "center", justifyContent: "center", padding: S.xl, gap: S.sm },
  emptyIcon:      { width: 56, height: 56, borderRadius: R.md, backgroundColor: C.primaryDim, alignItems: "center", justifyContent: "center", marginBottom: S.sm },
  emptyTitle:     { fontSize: F.lg, fontWeight: W.bold, color: C.text },
  emptySub:       { fontSize: F.xs, color: C.dim, letterSpacing: 0.5, textAlign: "center" },

  // Question bubble
  questionCard: { flexDirection: "row", backgroundColor: C.card, borderRadius: R.md, borderWidth: 1, borderColor: C.border, overflow: "hidden", shadowColor: "#001F6B", shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.06, shadowRadius: 3, elevation: 2 },
  questionAccent: { width: 3, backgroundColor: C.primary },
  questionBody: { flex: 1, padding: S.md, gap: S.xs },
  questionMeta: { flexDirection: "row", alignItems: "center", gap: S.sm },
  fragenLabel:  { flexDirection: "row", alignItems: "center", gap: 3 },
  fragenText:   { fontSize: 10, fontWeight: W.bold, color: C.primary, letterSpacing: 1.2 },
  catPill:      { backgroundColor: C.primaryDim, borderRadius: R.xs, paddingHorizontal: 7, paddingVertical: 2 },
  catText:      { fontSize: 10, color: C.primary, fontWeight: W.semi },
  topicName:    { fontSize: F.md, fontWeight: W.bold, color: C.text },
  topicPctRow:  { flexDirection: "row", alignItems: "center", gap: S.sm },
  topicPctText: { fontSize: F.xs, fontWeight: W.bold, minWidth: 32, textAlign: "right" },
  qDivider:     { height: 1, backgroundColor: C.border, marginVertical: S.xs },
  questionText: { fontSize: F.md, color: C.text, lineHeight: F.md * 1.65 },

  // User bubble (mirrors ChatScreen)
  userRow:    { flexDirection: "row", justifyContent: "flex-end" },
  userBubble: { backgroundColor: C.primary, borderRadius: R.md, borderBottomRightRadius: R.xs, paddingHorizontal: S.md, paddingVertical: S.sm + 2, maxWidth: "78%" },
  userText:   { color: C.card, fontSize: F.md, lineHeight: F.md * 1.55 },

  // Error bubble
  errorBubble: { flexDirection: "row", alignItems: "center", gap: S.sm, backgroundColor: C.redBg, borderRadius: R.md, paddingHorizontal: S.md, paddingVertical: S.sm + 2, borderWidth: 1, borderColor: C.red + "33" },
  errorText:   { fontSize: F.sm, color: C.red, flex: 1 },

  // Result bubble
  resultCard:   { flexDirection: "row", backgroundColor: C.card, borderRadius: R.md, borderWidth: 1, borderColor: C.border, overflow: "hidden", shadowColor: "#001F6B", shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.06, shadowRadius: 3, elevation: 2 },
  resultAccent: { width: 3 },
  resultBody:   { flex: 1, padding: S.md, gap: S.sm },
  resultTop:    { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between" },
  resultLabel:  { fontSize: 10, fontWeight: W.bold, color: C.dim, letterSpacing: 1.2 },
  resultStatus: { fontSize: F.sm, fontWeight: W.bold, marginTop: 2 },
  resultPct:    { fontSize: F.xxl, fontWeight: W.heavy },
  nextHint:     { fontSize: F.xs, color: C.mid },

  // Mastered
  masteredCard:  { backgroundColor: C.card, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.lg, alignItems: "center", gap: S.sm },
  masteredIcon:  { width: 56, height: 56, borderRadius: R.xl, backgroundColor: C.greenBg, alignItems: "center", justifyContent: "center" },
  masteredTitle: { fontSize: F.lg, fontWeight: W.bold, color: C.text },
  masteredSub:   { fontSize: F.sm, color: C.mid, textAlign: "center", lineHeight: 20 },

  // Weiter button
  weiterBtn:  { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: S.sm, backgroundColor: C.primary, borderRadius: R.md, paddingVertical: S.sm + 4, marginTop: S.xs },
  weiterText: { color: C.card, fontWeight: W.bold, fontSize: F.md },

  // Dashboard card
  dashCard:        { flexDirection: "row", backgroundColor: C.card, borderRadius: R.md, borderWidth: 1, borderColor: C.border, overflow: "hidden", shadowColor: "#001F6B", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.08, shadowRadius: 4, elevation: 3 },
  dashAccent:      { width: 3, backgroundColor: C.primary },
  dashBody:        { flex: 1, padding: S.md, gap: S.sm },
  dashHeaderRow:   { flexDirection: "row", alignItems: "flex-start", gap: S.sm },
  dashIconBox:     { width: 32, height: 32, borderRadius: R.sm, backgroundColor: C.primaryDim, alignItems: "center", justifyContent: "center" },
  dashTitle:       { fontSize: F.md, fontWeight: W.bold, color: C.text },
  dashSub:         { fontSize: 10, color: C.dim, marginTop: 1 },
  readyBadge:      { borderRadius: R.xs, paddingHorizontal: 7, paddingVertical: 3, alignSelf: "flex-start" },
  readyText:       { fontSize: 10, fontWeight: W.bold },
  dashOverallRow:  { flexDirection: "row", alignItems: "center", gap: S.sm },
  dashPctLarge:    { fontSize: F.xxl, fontWeight: W.heavy, color: C.primary, minWidth: 52 },
  dashDivider:     { height: 1, backgroundColor: C.border },
  // Stat tiles
  statRow:         { flexDirection: "row", gap: S.xs },
  statTile:        { flex: 1, borderRadius: R.xs, padding: S.xs + 2, alignItems: "center" },
  statCount:       { fontSize: F.lg, fontWeight: W.heavy },
  statLabel:       { fontSize: 9, fontWeight: W.semi, marginTop: 1 },
  // Category rows
  catHeaderRow:    { flexDirection: "row", alignItems: "center", gap: S.xs, paddingVertical: S.xs },
  dashCatName:     { fontSize: F.xs, color: C.mid, fontWeight: W.semi, marginBottom: 3 },
  dashCatBar:      { flex: 1 },
  dashCatPct:      { fontSize: F.xs, fontWeight: W.bold, minWidth: 30, textAlign: "right" },
  // Topic rows (expanded)
  topicRow:        { flexDirection: "row", alignItems: "center", gap: S.xs, paddingVertical: 5, paddingLeft: S.sm, borderLeftWidth: 2, borderLeftColor: C.border, marginLeft: 4, marginBottom: 2 },
  topicDot:        { width: 6, height: 6, borderRadius: 3, flexShrink: 0 },
  topicRowName:    { fontSize: F.xs, color: C.text, fontWeight: W.medium, width: 110 },
  topicBarWrap:    { flex: 1 },
  topicStatusBadge:{ borderRadius: R.xs, paddingHorizontal: 5, paddingVertical: 2 },
  topicStatusText: { fontSize: 9, fontWeight: W.bold },

  // Input area
  inputArea:   { borderTopWidth: 1, borderTopColor: C.border, backgroundColor: C.card, paddingHorizontal: S.sm, paddingVertical: S.sm, gap: S.xs },
  refInput:    { backgroundColor: C.bg, borderRadius: R.sm, borderWidth: 1, borderColor: C.border, paddingHorizontal: S.md, paddingVertical: S.sm, color: C.text, fontSize: F.sm },
  inputRow:    { flexDirection: "row", alignItems: "flex-end", gap: S.xs },
  refToggle:   { width: 36, height: 36, borderRadius: R.sm, alignItems: "center", justifyContent: "center", backgroundColor: C.bg, borderWidth: 1, borderColor: C.border },
  refToggleOn: { backgroundColor: C.primaryDim, borderColor: C.primary },
  input:       { flex: 1, backgroundColor: C.bg, borderRadius: R.lg, borderWidth: 1, borderColor: C.border, paddingHorizontal: S.md, paddingTop: 10, paddingBottom: 10, color: C.text, fontSize: F.md, maxHeight: 110 },
  inputFocused:{ borderColor: C.primary },
  sendBtn:     { width: 40, height: 40, borderRadius: R.full, backgroundColor: C.primary, alignItems: "center", justifyContent: "center" },
  sendBtnOff:  { backgroundColor: C.s2 },
});
