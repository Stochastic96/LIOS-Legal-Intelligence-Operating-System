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
import { api, BrainStatus, ChatResponse, getServerUrl, LLMModeStatus, setServerUrl } from "../api/client";
import ScalePressable from "../components/ScalePressable";
import TypingIndicator from "../components/TypingIndicator";
import UploadScreen from "./UploadScreen";
import { C, F, R, S, W } from "../theme";

const SESSION_ID = "lios-" + Date.now();

const QUICK_STARTS = [
  "Wer muss CSRD einhalten?",
  "Was sind ESRS-Berichtsstandards?",
  "EU-Taxonomie: grüne Kriterien",
  "SFDR-Klassifizierung von Fonds",
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

const CONF_LABEL: Record<string, string> = {
  high: "Hoch", medium: "Mittel", low: "Niedrig",
};

const CONF_COLOR: Record<string, string> = {
  high: C.green, medium: C.amber, low: C.red,
};

const CONF_BG: Record<string, string> = {
  high: C.greenBg, medium: C.amberBg, low: C.redBg,
};

function relativeTime(ts: number): string {
  const s = (Date.now() - ts) / 1000;
  if (s < 60)    return "Gerade eben";
  if (s < 3600)  return `vor ${Math.floor(s / 60)} Min.`;
  if (s < 86400) return `vor ${Math.floor(s / 3600)} Std.`;
  return new Date(ts).toLocaleDateString("de-DE");
}


export default function ChatScreen() {
  const [messages, setMessages]     = useState<Message[]>([]);
  const [input, setInput]           = useState("");
  const [loading, setLoading]       = useState(false);
  const [online, setOnline]         = useState<boolean | null>(null);
  const [inputFocused, setInputFocused] = useState(false);
  const [correction, setCorrection] = useState<{ msg: Message; type: "wrong" | "partial" } | null>(null);
  const [corrText, setCorrText]     = useState("");
  const [makeRule, setMakeRule]     = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [serverUrl, setServerUrlState] = useState("");
  const [uploadOpen, setUploadOpen]     = useState(false);
  const [brainStatus, setBrainStatus]   = useState<BrainStatus | null>(null);
  const [llmMode, setLlmMode]           = useState<LLMModeStatus | null>(null);
  const [brainLoading, setBrainLoading] = useState(false);
  const listRef  = useRef<FlatList>(null);
  const mountAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    api.health().then(() => setOnline(true)).catch(() => setOnline(false));
    getServerUrl().then(setServerUrlState);
    Animated.timing(mountAnim, { toValue: 1, duration: 300, useNativeDriver: true }).start();
  }, []);

  const loadBrainStatus = useCallback(async () => {
    setBrainLoading(true);
    try {
      const [status, mode] = await Promise.all([api.brain.status(), api.llmMode.get()]);
      setBrainStatus(status);
      setLlmMode(mode);
    } catch {}
    finally { setBrainLoading(false); }
  }, []);

  const openSettings = useCallback(() => {
    setSettingsOpen(true);
    loadBrainStatus();
  }, [loadBrainStatus]);

  const saveServerUrl = useCallback(async () => {
    await setServerUrl(serverUrl);
    setSettingsOpen(false);
    api.health().then(() => setOnline(true)).catch(() => setOnline(false));
  }, [serverUrl]);

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
          text: "Server nicht erreichbar.\n\nBitte starten: bash start.sh\nDann IP unter System → Server einstellen.",
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

  const renderItem = ({ item }: { item: Message }) => {
    const isUser = item.role === "user";
    if (isUser) {
      return (
        <View style={s.userRow}>
          <View style={s.userBubble}>
            <Text style={s.userText}>{item.text}</Text>
            <Text style={s.userTs}>{relativeTime(item.timestamp)}</Text>
          </View>
        </View>
      );
    }
    return (
      <View style={s.aiRow}>
        <View style={s.aiAvatar}>
          <Text style={s.aiAvatarText}>L</Text>
        </View>
        <View style={s.aiBubble}>
          <Text style={s.aiText}>{item.text}</Text>

          {item.confidence && (
            <View style={s.metaRow}>
              <View style={[s.confBadge, { backgroundColor: CONF_BG[item.confidence] ?? C.s2 }]}>
                <View style={[s.confDot, { backgroundColor: CONF_COLOR[item.confidence] ?? C.dim }]} />
                <Text style={[s.confText, { color: CONF_COLOR[item.confidence] ?? C.dim }]}>
                  {CONF_LABEL[item.confidence] ?? item.confidence}
                </Text>
              </View>
              {item.brain_used && (
                <View style={s.brainBadge}>
                  <Feather name="cpu" size={10} color={C.primary} />
                  <Text style={s.brainBadgeText}>KI aktiv</Text>
                </View>
              )}
              <Text style={s.aiTs}>{relativeTime(item.timestamp)}</Text>
            </View>
          )}

          {item.feedback === null && (
            <View style={s.fbRow}>
              <ScalePressable onPress={() => giveFeedback(item, "good")}>
                <View style={s.fbBtn}>
                  <Feather name="thumbs-up" size={12} color={C.green} />
                  <Text style={[s.fbBtnText, { color: C.green }]}>Korrekt</Text>
                </View>
              </ScalePressable>
              <ScalePressable onPress={() => { setCorrection({ msg: item, type: "wrong" }); setCorrText(""); setMakeRule(false); }}>
                <View style={s.fbBtn}>
                  <Feather name="thumbs-down" size={12} color={C.mid} />
                  <Text style={s.fbBtnText}>Falsch</Text>
                </View>
              </ScalePressable>
              <ScalePressable onPress={() => { setCorrection({ msg: item, type: "partial" }); setCorrText(""); setMakeRule(false); }}>
                <View style={s.fbBtn}>
                  <Feather name="edit-2" size={12} color={C.mid} />
                  <Text style={s.fbBtnText}>Ergänzen</Text>
                </View>
              </ScalePressable>
            </View>
          )}
          {item.feedback != null && (
            <Text style={s.fbDone}>
              {item.feedback === "good" ? "✓ Bestätigt" : item.feedback === "wrong" ? "Korrektur gespeichert" : "Ergänzung gespeichert"}
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
        <View style={s.headerLeft}>
          <View style={s.logoBox}>
            <Text style={s.logoText}>L</Text>
          </View>
          <View>
            <Text style={s.title}>LIOS</Text>
            <Text style={s.subtitle}>Rechts­intelligenz</Text>
          </View>
        </View>
        <View style={s.headerActions}>
          <View style={s.statusPill}>
            <View style={[s.statusDot, { backgroundColor: online === true ? C.online : online === false ? C.offline : C.dim }]} />
            <Text style={s.statusLabel}>{online === true ? "Verbunden" : online === false ? "Offline" : "…"}</Text>
          </View>
          <ScalePressable onPress={() => setUploadOpen(true)}>
            <View style={s.gearBtn}>
              <Feather name="upload-cloud" size={16} color={C.mid} />
            </View>
          </ScalePressable>
          <ScalePressable onPress={openSettings}>
            <View style={s.gearBtn}>
              <Feather name="settings" size={16} color={C.mid} />
            </View>
          </ScalePressable>
        </View>
      </View>

      <KeyboardAvoidingView
        style={s.flex}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={Platform.OS === "ios" ? 56 : 0}
      >
        <Animated.View style={[s.flex, { opacity: mountAnim }]}>
          <FlatList
            ref={listRef}
            data={messages}
            keyExtractor={(m) => m.id}
            renderItem={renderItem}
            style={s.flex}
            contentContainerStyle={messages.length === 0 ? s.emptyContainer : s.listContent}
            keyboardShouldPersistTaps="handled"
            onContentSizeChange={toBottom}
            ListEmptyComponent={
              <View style={s.empty}>
                <View style={s.emptyIcon}>
                  <Feather name="shield" size={28} color={C.primary} />
                </View>
                <Text style={s.emptyTitle}>Compliance-Assistent</Text>
                <Text style={s.emptySub}>
                  CSRD · ESRS · EU-Taxonomie · SFDR · DSGVO
                </Text>
                <View style={s.divider} />
                <Text style={s.quickLabel}>HÄUFIGE FRAGEN</Text>
                <View style={s.chipsGrid}>
                  {QUICK_STARTS.map((q) => (
                    <ScalePressable key={q} onPress={() => send(q)}>
                      <View style={s.chip}>
                        <Feather name="chevron-right" size={12} color={C.primary} />
                        <Text style={s.chipText}>{q}</Text>
                      </View>
                    </ScalePressable>
                  ))}
                </View>
              </View>
            }
          />
        </Animated.View>

        {loading && <TypingIndicator />}

        {/* Input bar */}
        <View style={s.inputBar}>
          <TextInput
            style={[s.input, inputFocused && s.inputFocused]}
            value={input}
            onChangeText={setInput}
            onFocus={() => setInputFocused(true)}
            onBlur={() => setInputFocused(false)}
            placeholder="Frage zum EU-Recht stellen…"
            placeholderTextColor={C.dim}
            multiline
            maxLength={500}
            onSubmitEditing={() => send()}
          />
          <ScalePressable onPress={() => send()} disabled={!input.trim() || loading}>
            <View style={[s.sendBtn, (!input.trim() || loading) && s.sendBtnOff]}>
              <Feather name="send" size={15} color={input.trim() && !loading ? C.card : C.dim} />
            </View>
          </ScalePressable>
        </View>
      </KeyboardAvoidingView>

      {/* Settings modal */}
      <Modal visible={settingsOpen} transparent animationType="slide">
        <KeyboardAvoidingView
          style={s.overlay}
          behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
          <Pressable style={s.flex} onPress={() => setSettingsOpen(false)} />
          <View style={s.sheet}>
            <View style={s.sheetHandle} />
            <Text style={s.sheetTitle}>System</Text>

            {/* Brain status section */}
            <View style={s.statusSection}>
              {brainLoading ? (
                <View style={s.statusRow}>
                  <Feather name="cpu" size={14} color={C.dim} />
                  <Text style={s.statusSectionText}>Lade Systemstatus…</Text>
                </View>
              ) : brainStatus ? (
                <>
                  <View style={s.statusRow}>
                    <View style={[s.statusDot, { backgroundColor: brainStatus.llm_reachable ? C.online : C.offline }]} />
                    <Text style={s.statusSectionText}>
                      KI: {brainStatus.llm_reachable ? "Erreichbar" : "Nicht erreichbar"}
                      {llmMode ? `  ·  ${llmMode.label}` : ""}
                    </Text>
                  </View>
                  <View style={s.statusRow}>
                    <Feather name="cpu" size={13} color={brainStatus.brain_on ? C.primary : C.dim} />
                    <Text style={s.statusSectionText}>
                      Gehirn: {brainStatus.brain_on ? "Aktiv" : "Inaktiv"}
                    </Text>
                    <Pressable
                      style={[s.brainToggle, brainStatus.brain_on && s.brainToggleOn]}
                      onPress={async () => {
                        const next = !brainStatus.brain_on;
                        const updated = await api.brain.toggle(next).catch(() => null);
                        if (updated) setBrainStatus(updated);
                      }}
                    >
                      <Text style={[s.brainToggleText, brainStatus.brain_on && s.brainToggleTextOn]}>
                        {brainStatus.brain_on ? "Ein" : "Aus"}
                      </Text>
                    </Pressable>
                  </View>
                  <View style={s.statusRow}>
                    <Feather name="database" size={13} color={C.dim} />
                    <Text style={s.statusSectionText}>
                      {brainStatus.knowledge_chunks} Chunks · {brainStatus.active_rules} Regeln · {brainStatus.total_corrections} Korrekturen
                    </Text>
                  </View>
                </>
              ) : (
                <View style={s.statusRow}>
                  <View style={[s.statusDot, { backgroundColor: C.offline }]} />
                  <Text style={s.statusSectionText}>Systemstatus nicht verfügbar</Text>
                </View>
              )}
            </View>

            <View style={s.sectionDivider} />
            <Text style={s.sheetSubtitle}>Server-Adresse</Text>
            <TextInput
              style={s.corrInput}
              value={serverUrl}
              onChangeText={setServerUrlState}
              placeholder="http://..."
              placeholderTextColor={C.dim}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
            />
            <View style={s.sheetBtns}>
              <ScalePressable onPress={() => setSettingsOpen(false)} style={{ flex: 1 }}>
                <View style={s.btnCancel}><Text style={s.btnCancelText}>Abbrechen</Text></View>
              </ScalePressable>
              <ScalePressable onPress={saveServerUrl} style={{ flex: 2 }}>
                <View style={s.btnSave}>
                  <Text style={s.btnSaveText}>Speichern</Text>
                </View>
              </ScalePressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* Upload modal */}
      <Modal visible={uploadOpen} animationType="slide" onRequestClose={() => setUploadOpen(false)}>
        <UploadScreen onClose={() => setUploadOpen(false)} />
      </Modal>

      {/* Correction modal */}
      <Modal visible={correction !== null} transparent animationType="slide">
        <KeyboardAvoidingView
          style={s.overlay}
          behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
          <Pressable style={s.flex} onPress={() => setCorrection(null)} />
          <View style={s.sheet}>
            <View style={s.sheetHandle} />
            <Text style={s.sheetTitle}>
              {correction?.type === "wrong" ? "Was ist korrekt?" : "Was fehlt in der Antwort?"}
            </Text>
            <TextInput
              style={s.corrInput}
              value={corrText}
              onChangeText={setCorrText}
              placeholder="Korrekte Information eingeben…"
              placeholderTextColor={C.dim}
              multiline
              autoFocus
              textAlignVertical="top"
            />
            <Pressable style={s.ruleRow} onPress={() => setMakeRule((v) => !v)}>
              <View style={[s.checkbox, makeRule && s.checkboxOn]}>
                {makeRule && <Feather name="check" size={10} color={C.card} />}
              </View>
              <Text style={s.ruleLabel}>Als dauerhafter Merksatz speichern</Text>
            </Pressable>
            <View style={s.sheetBtns}>
              <ScalePressable onPress={() => setCorrection(null)} style={{ flex: 1 }}>
                <View style={s.btnCancel}><Text style={s.btnCancelText}>Abbrechen</Text></View>
              </ScalePressable>
              <ScalePressable onPress={submitCorr} disabled={!corrText.trim()} style={{ flex: 2 }}>
                <View style={[s.btnSave, !corrText.trim() && s.btnOff]}>
                  <Text style={s.btnSaveText}>Speichern</Text>
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
  root:  { flex: 1, backgroundColor: C.bg },
  flex:  { flex: 1 },

  // Header
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: S.md, paddingVertical: S.sm + 2,
    backgroundColor: C.card,
    borderBottomWidth: 1, borderBottomColor: C.border,
  },
  headerLeft:  { flexDirection: "row", alignItems: "center", gap: S.sm },
  logoBox:     {
    width: 36, height: 36, borderRadius: R.sm,
    backgroundColor: C.primary, alignItems: "center", justifyContent: "center",
  },
  logoText:    { color: C.card, fontSize: F.md, fontWeight: W.heavy, letterSpacing: 1 },
  title:       { fontSize: F.lg, fontWeight: W.heavy, color: C.text, letterSpacing: 0.5 },
  subtitle:    { fontSize: 10, color: C.dim, letterSpacing: 0.8, marginTop: 1 },
  headerActions: { flexDirection: "row", alignItems: "center", gap: S.sm },
  statusPill:  {
    flexDirection: "row", alignItems: "center", gap: 5,
    backgroundColor: C.s2, borderRadius: R.full,
    paddingHorizontal: S.sm + 2, paddingVertical: 5,
    borderWidth: 1, borderColor: C.border,
  },
  statusDot:   { width: 6, height: 6, borderRadius: 3 },
  statusLabel: { fontSize: F.xs, color: C.mid, fontWeight: W.semi },
  gearBtn:     { width: 34, height: 34, borderRadius: R.sm, alignItems: "center", justifyContent: "center", backgroundColor: C.s2, borderWidth: 1, borderColor: C.border },

  // List
  listContent:    { paddingHorizontal: S.md, paddingVertical: S.md, gap: S.md },
  emptyContainer: { flex: 1 },

  // Empty state
  empty:       { flex: 1, alignItems: "center", justifyContent: "center", padding: S.xl },
  emptyIcon:   {
    width: 60, height: 60, borderRadius: R.md,
    backgroundColor: C.primaryDim, alignItems: "center", justifyContent: "center",
    marginBottom: S.md,
  },
  emptyTitle:  { fontSize: F.xl, fontWeight: W.bold, color: C.text, marginBottom: S.xs },
  emptySub:    { fontSize: F.xs, color: C.dim, letterSpacing: 0.5, textAlign: "center" },
  divider:     { width: 40, height: 1, backgroundColor: C.border, marginVertical: S.md },
  quickLabel:  { fontSize: 10, fontWeight: W.bold, color: C.dim, letterSpacing: 1.4, marginBottom: S.sm },
  chipsGrid:   { gap: S.sm, alignSelf: "stretch" },
  chip:        {
    flexDirection: "row", alignItems: "center", gap: S.xs,
    backgroundColor: C.card, borderRadius: R.sm,
    borderWidth: 1, borderColor: C.border,
    paddingHorizontal: S.md, paddingVertical: S.sm + 2,
    shadowColor: "#001F6B", shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05, shadowRadius: 2, elevation: 1,
  },
  chipText:    { fontSize: F.sm, color: C.mid, flex: 1 },

  // Messages — user
  userRow:    { flexDirection: "row", justifyContent: "flex-end" },
  userBubble: {
    backgroundColor: C.primary, borderRadius: R.md,
    borderBottomRightRadius: R.xs,
    paddingHorizontal: S.md, paddingVertical: S.sm + 2,
    maxWidth: "78%",
  },
  userText:   { color: C.card, fontSize: F.md, lineHeight: F.md * 1.55 },
  userTs:     { fontSize: 10, color: "rgba(255,255,255,0.55)", marginTop: 4, textAlign: "right" },

  // Messages — AI
  aiRow:      { flexDirection: "row", alignItems: "flex-start", gap: S.sm },
  aiAvatar:   {
    width: 30, height: 30, borderRadius: R.sm,
    backgroundColor: C.primary, alignItems: "center", justifyContent: "center",
    marginTop: 2, flexShrink: 0,
  },
  aiAvatarText: { color: C.card, fontSize: F.xs, fontWeight: W.heavy },
  aiBubble:   {
    flex: 1, backgroundColor: C.card, borderRadius: R.md,
    borderBottomLeftRadius: R.xs,
    paddingHorizontal: S.md, paddingVertical: S.sm + 2,
    borderWidth: 1, borderColor: C.border,
    shadowColor: "#001F6B", shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06, shadowRadius: 3, elevation: 2,
  },
  aiText:     { color: C.text, fontSize: F.md, lineHeight: F.md * 1.6 },
  aiTs:       { fontSize: 10, color: C.dim, marginLeft: "auto" as any },

  metaRow:    { flexDirection: "row", alignItems: "center", marginTop: S.sm, gap: S.xs, flexWrap: "wrap" },
  confBadge:  {
    flexDirection: "row", alignItems: "center", gap: 4,
    borderRadius: R.xs, paddingHorizontal: 7, paddingVertical: 3,
  },
  confDot:    { width: 5, height: 5, borderRadius: 3 },
  confText:   { fontSize: 10, fontWeight: W.semi, letterSpacing: 0.3 },
  brainBadge: {
    flexDirection: "row", alignItems: "center", gap: 3,
    backgroundColor: C.primaryDim, borderRadius: R.xs,
    paddingHorizontal: 6, paddingVertical: 3,
  },
  brainBadgeText: { fontSize: 10, color: C.primary, fontWeight: W.semi },

  fbRow:      { flexDirection: "row", marginTop: S.sm, gap: S.xs },
  fbBtn:      {
    flexDirection: "row", alignItems: "center", gap: 4,
    paddingHorizontal: S.sm, paddingVertical: 4,
    borderWidth: 1, borderColor: C.border, borderRadius: R.xs,
    backgroundColor: C.bg,
  },
  fbBtnText:  { fontSize: 10, color: C.mid, fontWeight: W.medium },
  fbDone:     { marginTop: S.sm, fontSize: F.xs, color: C.dim },

  // Input bar
  inputBar:   {
    flexDirection: "row", alignItems: "flex-end", gap: S.sm,
    paddingHorizontal: S.sm, paddingVertical: S.sm,
    borderTopWidth: 1, borderTopColor: C.border,
    backgroundColor: C.card,
  },
  input:      {
    flex: 1, backgroundColor: C.bg, borderRadius: R.lg,
    borderWidth: 1, borderColor: C.border,
    paddingHorizontal: S.md, paddingTop: 10, paddingBottom: 10,
    color: C.text, fontSize: F.md, maxHeight: 110,
  },
  inputFocused: { borderColor: C.primary },
  sendBtn:    {
    width: 40, height: 40, borderRadius: R.full,
    backgroundColor: C.primary, alignItems: "center", justifyContent: "center",
  },
  sendBtnOff: { backgroundColor: C.s2 },

  sheetSubtitle: { fontSize: F.sm, fontWeight: W.bold, color: C.mid, marginBottom: S.xs },
  sectionDivider: { height: 1, backgroundColor: C.border, marginVertical: S.sm },
  statusSection: { backgroundColor: C.s2, borderRadius: R.sm, padding: S.sm, gap: S.xs, marginBottom: S.xs },
  statusRow:    { flexDirection: "row", alignItems: "center", gap: S.sm },
  statusSectionText: { fontSize: F.sm, color: C.mid, flex: 1 },
  brainToggle:  { paddingHorizontal: S.sm, paddingVertical: 3, borderRadius: R.xs, borderWidth: 1, borderColor: C.border, backgroundColor: C.card },
  brainToggleOn: { backgroundColor: C.primaryDim, borderColor: C.primary },
  brainToggleText: { fontSize: F.xs, color: C.dim, fontWeight: W.semi },
  brainToggleTextOn: { color: C.primary },

  // Correction sheet
  overlay:    { flex: 1, backgroundColor: "rgba(15,28,51,0.45)", justifyContent: "flex-end" },
  sheet:      {
    backgroundColor: C.card, borderTopLeftRadius: R.lg, borderTopRightRadius: R.lg,
    padding: S.lg, paddingBottom: 40,
    borderTopWidth: 1, borderTopColor: C.border,
  },
  sheetHandle: { width: 36, height: 3, backgroundColor: C.border, borderRadius: 2, alignSelf: "center", marginBottom: S.md },
  sheetTitle:  { fontSize: F.lg, fontWeight: W.bold, color: C.text, marginBottom: S.sm },
  corrInput:   {
    backgroundColor: C.bg, borderRadius: R.md, padding: S.md,
    borderWidth: 1, borderColor: C.border,
    color: C.text, fontSize: F.md, minHeight: 80, marginBottom: S.sm,
  },
  ruleRow:     { flexDirection: "row", alignItems: "center", gap: S.sm, marginBottom: S.lg },
  checkbox:    { width: 18, height: 18, borderRadius: R.xs, borderWidth: 1.5, borderColor: C.border, alignItems: "center", justifyContent: "center" },
  checkboxOn:  { backgroundColor: C.primary, borderColor: C.primary },
  ruleLabel:   { fontSize: F.sm, color: C.mid },
  sheetBtns:   { flexDirection: "row", gap: S.sm },
  btnCancel:   { padding: S.sm + 2, borderRadius: R.md, backgroundColor: C.bg, alignItems: "center", borderWidth: 1, borderColor: C.border },
  btnCancelText: { color: C.mid, fontWeight: W.semi, fontSize: F.sm },
  btnSave:     { padding: S.sm + 2, borderRadius: R.md, backgroundColor: C.primary, alignItems: "center" },
  btnOff:      { opacity: 0.35 },
  btnSaveText: { color: C.card, fontWeight: W.bold, fontSize: F.sm },
});
