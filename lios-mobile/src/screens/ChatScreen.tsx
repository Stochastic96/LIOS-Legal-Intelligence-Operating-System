import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Animated,
  FlatList,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { api, ChatResponse } from "../api/client";
import ScalePressable from "../components/ScalePressable";
import { C, F, R, S, W } from "../theme";

const SESSION_ID = "lios-" + Date.now();

const QUICK_STARTS = [
  "What is CSRD and who must comply?",
  "Explain EU Taxonomy green criteria",
  "What are ESRS reporting standards?",
  "How does GDPR define personal data?",
];

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: number;
  confidence?: string;
  brain_used?: boolean;
  feedback?: "good" | "wrong" | "partial" | null;
}

const CONF_COLOR: Record<string, string> = {
  high: C.green, medium: C.amber, low: C.red,
};

function relativeTime(ts: number): string {
  const s = (Date.now() - ts) / 1000;
  if (s < 60)   return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400)return `${Math.floor(s / 3600)}h ago`;
  return new Date(ts).toLocaleDateString();
}

// 3-dot staggered pulse
function ThinkingDots() {
  const dots = [
    useRef(new Animated.Value(0.25)).current,
    useRef(new Animated.Value(0.25)).current,
    useRef(new Animated.Value(0.25)).current,
  ];
  useEffect(() => {
    const pulse = (a: Animated.Value, delay: number) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(a, { toValue: 1,    duration: 300, useNativeDriver: true }),
          Animated.timing(a, { toValue: 0.25, duration: 300, useNativeDriver: true }),
          Animated.delay(600 - delay),
        ])
      );
    const anims = dots.map((d, i) => pulse(d, i * 160));
    anims.forEach((a) => a.start());
    return () => anims.forEach((a) => a.stop());
  }, []);
  return (
    <View style={s.thinking}>
      {dots.map((d, i) => (
        <Animated.View key={i} style={[s.dot, { opacity: d }]} />
      ))}
      <Text style={s.thinkingText}>thinking</Text>
    </View>
  );
}

export default function ChatScreen() {
  const [messages, setMessages]   = useState<Message[]>([]);
  const [input, setInput]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [brainOn, setBrainOn]     = useState(true);
  const [inputFocused, setInputFocused] = useState(false);
  const [correction, setCorrection] = useState<{
    msg: Message; type: "wrong" | "partial";
  } | null>(null);
  const [corrText, setCorrText]   = useState("");
  const [makeRule, setMakeRule]   = useState(false);
  const listRef   = useRef<FlatList>(null);
  const mountAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const pulseLoop = useRef<Animated.CompositeAnimation | null>(null);

  useEffect(() => {
    api.brain.status().then((s) => setBrainOn(s.brain_on)).catch(() => {});
    Animated.timing(mountAnim, { toValue: 1, duration: 320, useNativeDriver: true }).start();
  }, []);

  // Pulse the brain status dot when on
  useEffect(() => {
    pulseLoop.current?.stop();
    if (brainOn) {
      pulseLoop.current = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 2.2, duration: 900, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1,   duration: 900, useNativeDriver: true }),
        ])
      );
      pulseLoop.current.start();
    } else {
      pulseAnim.setValue(1);
    }
    return () => pulseLoop.current?.stop();
  }, [brainOn]);

  const toBottom = useCallback(() => {
    setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 60);
  }, []);

  const send = useCallback(async (text?: string) => {
    const msg = (text ?? input).trim();
    if (!msg || loading) return;
    const userMsg: Message = { id: `u${Date.now()}`, role: "user", text: msg, timestamp: Date.now() };
    setMessages((p) => [...p, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res: ChatResponse = await api.chat.send(msg, SESSION_ID);
      setMessages((p) => [
        ...p,
        {
          id: res.message_id, role: "assistant", text: res.answer,
          timestamp: Date.now(),
          confidence: res.confidence, brain_used: res.brain_used, feedback: null,
        },
      ]);
    } catch {
      setMessages((p) => [
        ...p,
        {
          id: `e${Date.now()}`, role: "assistant", feedback: null, timestamp: Date.now(),
          text: "Server unreachable.\n\nRun:  bash start.sh\nThen set your IP in Brain → Settings",
        },
      ]);
    } finally {
      setLoading(false);
      toBottom();
    }
  }, [input, loading, toBottom]);

  const giveFeedback = useCallback(
    async (msg: Message, type: "good" | "wrong" | "partial", corr = "", rule = false) => {
      const idx = messages.findIndex((m) => m.id === msg.id);
      const q = idx > 0 ? messages[idx - 1].text : "";
      try {
        await api.feedback.submit({
          session_id: SESSION_ID, message_id: msg.id,
          query: q, original_answer: msg.text,
          feedback_type: type, correction_text: corr, make_rule: rule,
        });
      } catch {}
      setMessages((p) => p.map((m) => m.id === msg.id ? { ...m, feedback: type } : m));
    },
    [messages]
  );

  const submitCorr = useCallback(async () => {
    if (!correction || !corrText.trim()) return;
    await giveFeedback(correction.msg, correction.type, corrText.trim(), makeRule);
    setCorrection(null); setCorrText(""); setMakeRule(false);
  }, [correction, corrText, makeRule, giveFeedback]);

  const openCorr = (msg: Message, type: "wrong" | "partial") => {
    setCorrection({ msg, type }); setCorrText(""); setMakeRule(false);
  };

  const renderItem = ({ item }: { item: Message }) => {
    const isUser = item.role === "user";
    return (
      <View style={[s.msgWrap, isUser && s.msgWrapUser]}>
        {!isUser && (
          <View style={s.msgCol}>
            <View style={s.lTag}><Text style={s.lTagText}>L</Text></View>
            <View style={s.msgLine} />
          </View>
        )}
        <View style={isUser ? s.msgBodyUser : s.msgBodyAI}>
          <Text style={[s.msgText, isUser && s.msgTextUser]}>{item.text}</Text>

          {!isUser && item.confidence && (
            <View style={s.metaRow}>
              <View style={[s.metaDot, { backgroundColor: CONF_COLOR[item.confidence] ?? C.dim }]} />
              <Text style={s.metaText}>{item.confidence}</Text>
              {item.brain_used && (
                <Text style={[s.metaText, { color: C.accent, marginLeft: S.sm }]}>brain</Text>
              )}
              <Text style={[s.metaText, { marginLeft: "auto" as any }]}>{relativeTime(item.timestamp)}</Text>
            </View>
          )}

          {isUser && (
            <Text style={s.tsUser}>{relativeTime(item.timestamp)}</Text>
          )}

          {!isUser && item.feedback === null && (
            <View style={s.fbRow}>
              <ScalePressable onPress={() => giveFeedback(item, "good")}>
                <View style={s.fbGood}>
                  <Feather name="check" size={12} color={C.green} />
                </View>
              </ScalePressable>
              <ScalePressable onPress={() => openCorr(item, "wrong")}>
                <View style={s.fbBad}>
                  <Feather name="x" size={12} color={C.mid} />
                  <Text style={s.fbBadText}>wrong</Text>
                </View>
              </ScalePressable>
              <ScalePressable onPress={() => openCorr(item, "partial")}>
                <View style={s.fbBad}>
                  <Feather name="minus" size={12} color={C.mid} />
                  <Text style={s.fbBadText}>partial</Text>
                </View>
              </ScalePressable>
            </View>
          )}
          {!isUser && item.feedback != null && (
            <Text style={s.fbDone}>
              {item.feedback === "good" ? "noted ✓" : item.feedback === "wrong" ? "corrected" : "noted ~"}
            </Text>
          )}
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={s.root} edges={["top"]}>
      {/* Header */}
      <View style={s.header}>
        <Text style={s.logo}>LIOS</Text>
        <View style={s.statusRow}>
          {/* Pulsing halo behind the dot */}
          <View style={s.dotWrap}>
            {brainOn && (
              <Animated.View
                style={[
                  s.statusHalo,
                  { transform: [{ scale: pulseAnim }], opacity: pulseAnim.interpolate({ inputRange: [1, 2.2], outputRange: [0.5, 0] }) },
                ]}
              />
            )}
            <View style={[s.statusDot, { backgroundColor: brainOn ? C.green : C.dim }]} />
          </View>
          <Text style={s.statusText}>{brainOn ? "brain on" : "brain off"}</Text>
        </View>
      </View>

      <KeyboardAvoidingView
        style={s.flex}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={Platform.OS === "ios" ? 56 : 0}
      >
        <Animated.View
          style={[s.flex, {
            opacity: mountAnim,
            transform: [{ translateY: mountAnim.interpolate({ inputRange: [0, 1], outputRange: [12, 0] }) }],
          }]}
        >
          <FlatList
            ref={listRef}
            data={messages}
            keyExtractor={(m) => m.id}
            renderItem={renderItem}
            style={s.flex}
            contentContainerStyle={messages.length === 0 ? s.emptyContainer : s.list}
            keyboardShouldPersistTaps="handled"
            onContentSizeChange={toBottom}
            ListEmptyComponent={
              <View style={s.empty}>
                <Feather name="feather" size={36} color={C.dim} style={{ marginBottom: S.md }} />
                <Text style={s.emptyTitle}>Ask LIOS</Text>
                <Text style={s.emptySub}>EU law · Compliance · Sustainability</Text>
                {/* Quick-start chips */}
                <View style={s.chipsWrap}>
                  {QUICK_STARTS.map((q) => (
                    <ScalePressable key={q} onPress={() => send(q)}>
                      <View style={s.chip}>
                        <Text style={s.chipText}>{q}</Text>
                      </View>
                    </ScalePressable>
                  ))}
                </View>
              </View>
            }
          />
        </Animated.View>

        {loading && <ThinkingDots />}

        {/* Input bar */}
        <View style={s.bar}>
          <TextInput
            style={[s.input, inputFocused && s.inputFocused]}
            value={input}
            onChangeText={setInput}
            onFocus={() => setInputFocused(true)}
            onBlur={() => setInputFocused(false)}
            placeholder="Ask about EU law…"
            placeholderTextColor={C.dim}
            multiline={true}
            maxLength={500}
            onSubmitEditing={() => send()}
          />
          <ScalePressable onPress={() => send()} disabled={!input.trim() || loading}>
            <View style={[s.send, (!input.trim() || loading) && s.sendOff]}>
              <Feather name="send" size={16} color={input.trim() && !loading ? C.bg : C.dim} />
            </View>
          </ScalePressable>
        </View>
      </KeyboardAvoidingView>

      {/* Correction modal */}
      <Modal visible={correction !== null} transparent animationType="slide">
        <KeyboardAvoidingView
          style={s.overlay}
          behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
          <Pressable style={s.flex} onPress={() => setCorrection(null)} />
          <View style={s.sheet}>
            <View style={s.sheetBar} />
            <Text style={s.sheetTitle}>
              {correction?.type === "wrong" ? "What is correct?" : "What was missing?"}
            </Text>
            <TextInput
              style={s.corrInput}
              value={corrText}
              onChangeText={setCorrText}
              placeholder="Type the correction…"
              placeholderTextColor={C.dim}
              multiline autoFocus textAlignVertical="top"
            />
            <Pressable style={s.ruleRow} onPress={() => setMakeRule((v) => !v)}>
              <View style={[s.checkbox, makeRule && s.checkboxOn]}>
                {makeRule && <Feather name="check" size={11} color={C.bg} />}
              </View>
              <Text style={s.ruleLabel}>Remember as permanent rule</Text>
            </Pressable>
            <View style={s.sheetBtns}>
              <ScalePressable onPress={() => setCorrection(null)} style={{ flex: 1 }}>
                <View style={s.btnCancel}><Text style={s.btnCancelText}>Cancel</Text></View>
              </ScalePressable>
              <ScalePressable onPress={submitCorr} disabled={!corrText.trim()} style={{ flex: 2 }}>
                <View style={[s.btnSave, !corrText.trim() && s.btnOff]}>
                  <Text style={s.btnSaveText}>Save</Text>
                </View>
              </ScalePressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  root:       { flex: 1, backgroundColor: C.bg },
  flex:       { flex: 1 },

  header:     {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: S.md + 2, paddingVertical: S.sm + 2,
    borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: C.border,
  },
  logo:       { fontSize: F.lg, fontWeight: W.heavy, color: C.accent, letterSpacing: 3 },
  statusRow:  { flexDirection: "row", alignItems: "center", gap: 6 },
  dotWrap:    { width: 14, height: 14, alignItems: "center", justifyContent: "center" },
  statusHalo: {
    position: "absolute",
    width: 14, height: 14, borderRadius: 7,
    backgroundColor: C.green,
  },
  statusDot:  { width: 7, height: 7, borderRadius: 4 },
  statusText: { fontSize: F.xs, color: C.mid, letterSpacing: 0.5 },

  list:          { paddingHorizontal: S.md, paddingTop: S.sm, paddingBottom: S.sm },
  emptyContainer:{ flex: 1 },
  empty:         { flex: 1, alignItems: "center", justifyContent: "center", padding: S.lg },
  emptyTitle:    { fontSize: F.xl, fontWeight: W.bold, color: C.text, marginBottom: S.xs },
  emptySub:      { fontSize: F.xs, color: C.dim, letterSpacing: 0.8, marginBottom: S.lg },
  chipsWrap:     { gap: S.sm, alignSelf: "stretch" },
  chip:          {
    backgroundColor: C.s2, borderRadius: R.sm,
    borderWidth: 1, borderColor: C.border,
    paddingHorizontal: S.md, paddingVertical: S.sm + 2,
  },
  chipText:      { fontSize: F.sm, color: C.mid, lineHeight: 18 },

  msgWrap:    { flexDirection: "row", marginBottom: S.lg, alignItems: "flex-start" },
  msgWrapUser:{ justifyContent: "flex-end" },
  msgCol:     { alignItems: "center", marginRight: S.sm, width: 18 },
  lTag:       { width: 18, height: 18, borderRadius: R.xs, backgroundColor: C.accent, alignItems: "center", justifyContent: "center" },
  lTagText:   { color: C.bg, fontSize: 10, fontWeight: W.heavy },
  msgLine:    { flex: 1, width: 1, backgroundColor: C.border, marginTop: 3 },
  msgBodyAI:  {
    flex: 1, backgroundColor: C.s2, borderRadius: R.md,
    paddingHorizontal: S.md, paddingVertical: S.sm,
    borderWidth: StyleSheet.hairlineWidth, borderColor: C.border,
    borderLeftWidth: 3, borderLeftColor: C.accent,
  },
  msgBodyUser:{
    backgroundColor: C.userMsg, borderRadius: R.md,
    paddingHorizontal: S.md, paddingVertical: S.sm,
    borderWidth: StyleSheet.hairlineWidth, borderColor: C.accentPress,
    maxWidth: "78%",
  },
  msgText:    { color: C.text, fontSize: F.md, lineHeight: F.md * 1.55 },
  msgTextUser:{ color: C.userText },
  tsUser:     { fontSize: 10, color: C.dim, marginTop: 4, textAlign: "right" },

  metaRow:    { flexDirection: "row", alignItems: "center", marginTop: S.sm, gap: 5 },
  metaDot:    { width: 5, height: 5, borderRadius: 3 },
  metaText:   { fontSize: F.xs, color: C.dim, letterSpacing: 0.5 },

  fbRow:      { flexDirection: "row", marginTop: S.sm, gap: S.xs },
  fbGood:     { paddingHorizontal: S.sm, paddingVertical: 4, borderWidth: 1, borderColor: C.green, borderRadius: R.sm, alignItems: "center", justifyContent: "center" },
  fbBad:      { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: S.sm, paddingVertical: 4, borderWidth: 1, borderColor: C.border, borderRadius: R.sm },
  fbBadText:  { color: C.mid, fontSize: F.xs },
  fbDone:     { marginTop: S.sm, fontSize: F.xs, color: C.dim },

  thinking:   { flexDirection: "row", alignItems: "center", gap: 5, paddingHorizontal: S.md + 2, paddingVertical: S.xs },
  dot:        { width: 6, height: 6, borderRadius: 3, backgroundColor: C.accent },
  thinkingText:{ fontSize: F.xs, color: C.dim, letterSpacing: 0.8, marginLeft: 4 },

  bar:        {
    flexDirection: "row", alignItems: "flex-end", gap: S.sm,
    paddingHorizontal: S.sm, paddingVertical: S.sm,
    borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: C.border, backgroundColor: C.bg,
  },
  input:      {
    flex: 1, backgroundColor: C.s1, borderRadius: R.lg,
    borderWidth: StyleSheet.hairlineWidth, borderColor: C.border,
    paddingHorizontal: S.md, paddingTop: 10, paddingBottom: 10,
    color: C.text, fontSize: F.md, maxHeight: 110,
  },
  inputFocused:{ borderColor: C.borderBright },
  send:       { width: 40, height: 40, borderRadius: R.full, backgroundColor: C.accent, alignItems: "center", justifyContent: "center" },
  sendOff:    { backgroundColor: C.s2 },

  overlay:    { flex: 1, backgroundColor: "rgba(0,0,0,0.65)", justifyContent: "flex-end" },
  sheet:      { backgroundColor: C.s3, borderTopLeftRadius: R.lg, borderTopRightRadius: R.lg, padding: S.lg, paddingBottom: 40, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: C.border },
  sheetBar:   { width: 32, height: 3, backgroundColor: C.border, borderRadius: 2, alignSelf: "center", marginBottom: S.md + 2 },
  sheetTitle: { fontSize: F.md, fontWeight: W.bold, color: C.text, marginBottom: S.sm },
  corrInput:  { backgroundColor: C.s2, borderRadius: R.md, padding: S.sm, borderWidth: StyleSheet.hairlineWidth, borderColor: C.border, color: C.text, fontSize: F.md, minHeight: 80, marginBottom: S.sm },
  ruleRow:    { flexDirection: "row", alignItems: "center", gap: S.sm, marginBottom: S.lg },
  checkbox:   { width: 18, height: 18, borderRadius: R.xs, borderWidth: 1.5, borderColor: C.border, alignItems: "center", justifyContent: "center" },
  checkboxOn: { backgroundColor: C.accent, borderColor: C.accent },
  ruleLabel:  { fontSize: F.sm, color: C.mid },
  sheetBtns:  { flexDirection: "row", gap: S.sm },
  btnCancel:  { padding: S.sm, borderRadius: R.md, backgroundColor: C.s2, alignItems: "center", borderWidth: StyleSheet.hairlineWidth, borderColor: C.border },
  btnCancelText:{ color: C.mid, fontWeight: W.semi, fontSize: F.sm },
  btnSave:    { padding: S.sm, borderRadius: R.md, backgroundColor: C.accent, alignItems: "center" },
  btnOff:     { opacity: 0.35 },
  btnSaveText:{ color: C.bg, fontWeight: W.bold, fontSize: F.sm },
});
