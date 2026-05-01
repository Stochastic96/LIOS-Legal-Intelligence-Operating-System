import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
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
import { api, ChatResponse } from "../api/client";
import { C, F, R } from "../theme";

const SESSION_ID = "lios-" + Date.now();

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  confidence?: string;
  brain_used?: boolean;
  feedback?: "good" | "wrong" | "partial" | null;
}

const CONF_COLOR: Record<string, string> = {
  high: C.green, medium: C.amber, low: C.red,
};

export default function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [brainOn, setBrainOn] = useState(true);
  const [correction, setCorrection] = useState<{ msg: Message; type: "wrong" | "partial" } | null>(null);
  const [corrText, setCorrText] = useState("");
  const [makeRule, setMakeRule] = useState(false);
  const listRef = useRef<FlatList>(null);

  useEffect(() => {
    api.brain.status().then((s) => setBrainOn(s.brain_on)).catch(() => {});
  }, []);

  const toBottom = useCallback(() => {
    setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 60);
  }, []);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    const userMsg: Message = { id: `u${Date.now()}`, role: "user", text };
    setMessages((p) => [...p, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res: ChatResponse = await api.chat.send(text, SESSION_ID);
      setMessages((p) => [
        ...p,
        { id: res.message_id, role: "assistant", text: res.answer,
          confidence: res.confidence, brain_used: res.brain_used, feedback: null },
      ]);
    } catch {
      setMessages((p) => [
        ...p,
        { id: `e${Date.now()}`, role: "assistant",
          text: "Server unreachable.\n\nRun:  bash start.sh\nThen set your IP in Brain → ⚙", feedback: null },
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

  const renderItem = ({ item, index }: { item: Message; index: number }) => {
    const isUser = item.role === "user";
    return (
      <View style={[s.msgWrap, isUser && s.msgWrapUser]}>
        {!isUser && (
          <View style={s.msgCol}>
            <View style={s.lTag}><Text style={s.lTagText}>L</Text></View>
            <View style={s.msgLine} />
          </View>
        )}
        <View style={[s.msgBody, isUser && s.msgBodyUser]}>
          <Text style={[s.msgText, isUser && s.msgTextUser]}>{item.text}</Text>

          {!isUser && item.confidence && (
            <View style={s.metaRow}>
              <View style={[s.dot, { backgroundColor: CONF_COLOR[item.confidence] ?? C.dim }]} />
              <Text style={s.metaText}>{item.confidence}</Text>
              {item.brain_used && <Text style={[s.metaText, { color: C.accent, marginLeft: 8 }]}>brain</Text>}
            </View>
          )}

          {!isUser && item.feedback === null && (
            <View style={s.fbRow}>
              <Pressable style={s.fbGood} onPress={() => giveFeedback(item, "good")}>
                <Text style={s.fbGoodText}>✓</Text>
              </Pressable>
              <Pressable style={s.fbBad} onPress={() => { setCorrection({ msg: item, type: "wrong" }); setCorrText(""); setMakeRule(false); }}>
                <Text style={s.fbBadText}>✗ wrong</Text>
              </Pressable>
              <Pressable style={s.fbBad} onPress={() => { setCorrection({ msg: item, type: "partial" }); setCorrText(""); setMakeRule(false); }}>
                <Text style={s.fbBadText}>~ partial</Text>
              </Pressable>
            </View>
          )}
          {!isUser && item.feedback != null && (
            <Text style={s.fbDone}>
              {item.feedback === "good" ? "✓ noted" : item.feedback === "wrong" ? "✗ corrected" : "~ noted"}
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
          <View style={[s.statusDot, { backgroundColor: brainOn ? C.green : C.dim }]} />
          <Text style={s.statusText}>{brainOn ? "brain on" : "brain off"}</Text>
        </View>
      </View>

      <KeyboardAvoidingView
        style={s.flex}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={Platform.OS === "ios" ? 56 : 0}
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
              <Text style={s.emptyGlyph}>⚖</Text>
              <Text style={s.emptyTitle}>Ask LIOS</Text>
              <Text style={s.emptySub}>CSRD · EU Taxonomy · SFDR · ESRS</Text>
            </View>
          }
        />

        {loading && (
          <View style={s.thinking}>
            <ActivityIndicator size="small" color={C.accent} />
            <Text style={s.thinkingText}>thinking</Text>
          </View>
        )}

        <View style={s.bar}>
          <TextInput
            style={s.input}
            value={input}
            onChangeText={setInput}
            placeholder="Ask about EU law…"
            placeholderTextColor={C.dim}
            multiline={true}
            maxLength={500}
          />
          <Pressable
            style={[s.send, (!input.trim() || loading) && s.sendOff]}
            onPress={send}
            disabled={!input.trim() || loading}
          >
            <Text style={s.sendIcon}>↑</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>

      <Modal visible={correction !== null} transparent={true} animationType="slide">
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
              multiline={true}
              autoFocus={true}
              textAlignVertical="top"
            />
            <Pressable style={s.ruleRow} onPress={() => setMakeRule((v) => !v)}>
              <View style={[s.checkbox, makeRule && s.checkboxOn]} />
              <Text style={s.ruleLabel}>Remember as permanent rule</Text>
            </Pressable>
            <View style={s.sheetBtns}>
              <Pressable style={s.btnCancel} onPress={() => setCorrection(null)}>
                <Text style={s.btnCancelText}>Cancel</Text>
              </Pressable>
              <Pressable
                style={[s.btnSave, !corrText.trim() && s.btnOff]}
                onPress={submitCorr}
                disabled={!corrText.trim()}
              >
                <Text style={s.btnSaveText}>Save</Text>
              </Pressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  root:    { flex: 1, backgroundColor: C.bg },
  flex:    { flex: 1 },
  header:  { flexDirection: "row", alignItems: "center", justifyContent: "space-between",
             paddingHorizontal: 18, paddingVertical: 12,
             borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: C.border },
  logo:    { fontSize: F.lg, fontWeight: "800", color: C.text, letterSpacing: 2 },
  statusRow: { flexDirection: "row", alignItems: "center", gap: 5 },
  statusDot: { width: 6, height: 6, borderRadius: 3 },
  statusText: { fontSize: F.xs, color: C.mid, letterSpacing: 0.5 },
  list:    { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 8 },
  emptyContainer: { flex: 1 },
  empty:   { flex: 1, alignItems: "center", justifyContent: "center" },
  emptyGlyph: { fontSize: 44, color: C.dim, marginBottom: 16 },
  emptyTitle: { fontSize: F.xl, fontWeight: "700", color: C.text, marginBottom: 6 },
  emptySub:   { fontSize: F.sm, color: C.dim, letterSpacing: 0.5 },
  msgWrap:    { flexDirection: "row", marginBottom: 20, alignItems: "flex-start" },
  msgWrapUser:{ justifyContent: "flex-end" },
  msgCol:     { alignItems: "center", marginRight: 10, width: 18 },
  lTag:       { width: 18, height: 18, borderRadius: 2, backgroundColor: C.accent,
                alignItems: "center", justifyContent: "center" },
  lTagText:   { color: "#fff", fontSize: 10, fontWeight: "900" },
  msgLine:    { flex: 1, width: 1, backgroundColor: C.border, marginTop: 3 },
  msgBody:    { flex: 1, backgroundColor: C.s2, borderRadius: R.md,
                paddingHorizontal: 14, paddingVertical: 10,
                borderWidth: StyleSheet.hairlineWidth, borderColor: C.border },
  msgBodyUser:{ backgroundColor: C.accentDim, borderColor: C.accent, maxWidth: "78%", flex: 0 },
  msgText:    { color: C.text, fontSize: F.md, lineHeight: 22 },
  msgTextUser:{ color: "#c8d8ff" },
  metaRow:    { flexDirection: "row", alignItems: "center", marginTop: 8, gap: 5 },
  dot:        { width: 5, height: 5, borderRadius: 3 },
  metaText:   { fontSize: F.xs, color: C.dim, letterSpacing: 0.5 },
  fbRow:      { flexDirection: "row", marginTop: 10, gap: 6 },
  fbGood:     { paddingHorizontal: 10, paddingVertical: 4,
                borderWidth: 1, borderColor: C.green, borderRadius: R.sm },
  fbGoodText: { color: C.green, fontSize: F.xs, fontWeight: "700" },
  fbBad:      { paddingHorizontal: 10, paddingVertical: 4,
                borderWidth: 1, borderColor: C.border, borderRadius: R.sm },
  fbBadText:  { color: C.mid, fontSize: F.xs },
  fbDone:     { marginTop: 8, fontSize: F.xs, color: C.dim },
  thinking:   { flexDirection: "row", alignItems: "center", gap: 8,
                paddingHorizontal: 18, paddingVertical: 6 },
  thinkingText: { fontSize: F.xs, color: C.dim, letterSpacing: 1 },
  bar:        { flexDirection: "row", alignItems: "flex-end", gap: 8,
                paddingHorizontal: 12, paddingVertical: 10,
                borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: C.border,
                backgroundColor: C.bg },
  input:      { flex: 1, backgroundColor: C.s1,
                borderRadius: R.lg, borderWidth: StyleSheet.hairlineWidth, borderColor: C.border,
                paddingHorizontal: 16, paddingTop: 10, paddingBottom: 10,
                color: C.text, fontSize: F.md, maxHeight: 110 },
  send:       { width: 40, height: 40, borderRadius: R.full, backgroundColor: C.accent,
                alignItems: "center", justifyContent: "center" },
  sendOff:    { backgroundColor: C.s2 },
  sendIcon:   { color: "#fff", fontSize: 17, fontWeight: "800" },
  // Modal
  overlay:    { flex: 1, backgroundColor: "rgba(0,0,0,0.65)", justifyContent: "flex-end" },
  sheet:      { backgroundColor: C.s1, borderTopLeftRadius: 20, borderTopRightRadius: 20,
                padding: 20, paddingBottom: 40,
                borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: C.border },
  sheetBar:   { width: 32, height: 3, backgroundColor: C.border, borderRadius: 2,
                alignSelf: "center", marginBottom: 18 },
  sheetTitle: { fontSize: F.md, fontWeight: "700", color: C.text, marginBottom: 12 },
  corrInput:  { backgroundColor: C.s2, borderRadius: R.md, padding: 12,
                borderWidth: StyleSheet.hairlineWidth, borderColor: C.border,
                color: C.text, fontSize: F.md, minHeight: 80, marginBottom: 14 },
  ruleRow:    { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 20 },
  checkbox:   { width: 18, height: 18, borderRadius: 4, borderWidth: 1.5, borderColor: C.border },
  checkboxOn: { backgroundColor: C.accent, borderColor: C.accent },
  ruleLabel:  { fontSize: F.sm, color: C.mid },
  sheetBtns:  { flexDirection: "row", gap: 10 },
  btnCancel:  { flex: 1, padding: 12, borderRadius: R.md, backgroundColor: C.s2,
                alignItems: "center", borderWidth: StyleSheet.hairlineWidth, borderColor: C.border },
  btnCancelText: { color: C.mid, fontWeight: "600", fontSize: F.sm },
  btnSave:    { flex: 2, padding: 12, borderRadius: R.md, backgroundColor: C.accent, alignItems: "center" },
  btnOff:     { opacity: 0.35 },
  btnSaveText:{ color: "#fff", fontWeight: "700", fontSize: F.sm },
});
