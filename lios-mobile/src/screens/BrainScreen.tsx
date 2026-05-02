import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Animated,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { api, BrainStatus, Rule, getServerUrl, setServerUrl } from "../api/client";
import { C, F, R, S, W } from "../theme";
import ScalePressable from "../components/ScalePressable";
import Card from "../components/Card";
import SectionHeader from "../components/SectionHeader";

// ── Custom animated pill toggle ───────────────────────────────────────────────
function PillToggle({ value, onToggle, disabled }: { value: boolean; onToggle: (v: boolean) => void; disabled?: boolean }) {
  const anim = useRef(new Animated.Value(value ? 1 : 0)).current;

  useEffect(() => {
    Animated.spring(anim, { toValue: value ? 1 : 0, useNativeDriver: false, speed: 20, bounciness: 6 }).start();
  }, [value]);

  const bgColor = anim.interpolate({ inputRange: [0, 1], outputRange: [C.s2, C.accent] });
  const translateX = anim.interpolate({ inputRange: [0, 1], outputRange: [2, 22] });

  return (
    <Pressable onPress={() => !disabled && onToggle(!value)} style={{ opacity: disabled ? 0.5 : 1 }}>
      <Animated.View style={[styles.pillTrack, { backgroundColor: bgColor }]}>
        <Animated.View style={[styles.pillThumb, { transform: [{ translateX }] }]} />
      </Animated.View>
    </Pressable>
  );
}

// ── Info badge ────────────────────────────────────────────────────────────────
function InfoBadge({ label, value, icon, valueColor }: {
  label: string; value: string;
  icon: React.ComponentProps<typeof Feather>["name"];
  valueColor?: string;
}) {
  return (
    <View style={styles.infoBadge}>
      <Feather name={icon} size={13} color={C.dim} style={{ marginBottom: 4 }} />
      <Text style={styles.infoBadgeLabel}>{label}</Text>
      <Text style={[styles.infoBadgeValue, valueColor ? { color: valueColor } : {}]}>{value}</Text>
    </View>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────
export default function BrainScreen() {
  const [status, setStatus] = useState<BrainStatus | null>(null);
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [addRuleModal, setAddRuleModal] = useState(false);
  const [ruleText, setRuleText] = useState("");
  const [ruleTopic, setRuleTopic] = useState("general");
  const [serverUrlModal, setServerUrlModal] = useState(false);
  const [urlInput, setUrlInput] = useState("");

  const mountAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(mountAnim, { toValue: 1, duration: 320, useNativeDriver: true }).start();
  }, []);

  const translateY = mountAnim.interpolate({ inputRange: [0, 1], outputRange: [16, 0] });

  const loadAll = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true); else setLoading(true);
    try {
      const [s, r] = await Promise.all([api.brain.status(), api.memory.rules()]);
      setStatus(s);
      setRules(r.rules);
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const toggleBrain = useCallback(async (val: boolean) => {
    setToggling(true);
    try {
      const res = await api.brain.toggle(val);
      setStatus((prev) => prev ? { ...prev, brain_on: res.brain_on } : prev);
    } finally {
      setToggling(false);
    }
  }, []);

  const addRule = useCallback(async () => {
    if (!ruleText.trim()) return;
    try {
      const res = await api.memory.addRule(ruleText.trim(), ruleTopic.trim() || "general");
      setRules((prev) => [...prev, res.rule]);
      setRuleText(""); setRuleTopic("general"); setAddRuleModal(false);
    } catch {
      Alert.alert("Error", "Could not add rule.");
    }
  }, [ruleText, ruleTopic]);

  const removeRule = useCallback(async (id: string) => {
    Alert.alert("Remove Rule", "Deactivate this rule?", [
      { text: "Cancel", style: "cancel" },
      { text: "Remove", style: "destructive", onPress: async () => {
        try {
          await api.memory.deleteRule(id);
          setRules((prev) => prev.filter((r) => r.id !== id));
        } catch {}
      }},
    ]);
  }, []);

  const saveServerUrl = useCallback(async () => {
    await setServerUrl(urlInput.trim());
    setServerUrlModal(false); loadAll();
  }, [urlInput, loadAll]);

  const openServerUrl = useCallback(async () => {
    const current = await getServerUrl();
    setUrlInput(current); setServerUrlModal(true);
  }, []);

  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={["top"]}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={C.accent} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Brain</Text>
        <ScalePressable onPress={openServerUrl}>
          <View style={styles.serverBtn}>
            <Feather name="settings" size={13} color={C.mid} />
            <Text style={styles.serverBtnText}>Server</Text>
          </View>
        </ScalePressable>
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => loadAll(true)} tintColor={C.accent} />}
      >
        <Animated.View style={{ opacity: mountAnim, transform: [{ translateY }] }}>
          {/* Brain card */}
          <Card style={styles.brainCard}>
            <View style={styles.brainRow}>
              <View style={styles.brainLeft}>
                <Feather name="cpu" size={20} color={status?.brain_on ? C.accent : C.dim} />
                <View style={{ marginLeft: S.sm }}>
                  <Text style={styles.cardTitle}>Brain</Text>
                  <Text style={styles.cardSub}>
                    {status?.brain_on ? "LLM-powered answers active" : "Rule-based fallback only"}
                  </Text>
                </View>
              </View>
              <PillToggle value={status?.brain_on ?? false} onToggle={toggleBrain} disabled={toggling} />
            </View>

            <View style={styles.divider} />

            <View style={styles.badgeGrid}>
              <InfoBadge label="Model"  icon="box"       value={status?.model ?? "—"} />
              <InfoBadge label="LLM"    icon="wifi"      value={status?.llm_reachable ? "Online" : "Offline"}
                valueColor={status?.llm_reachable ? C.green : C.red} />
              <InfoBadge label="Chunks" icon="database"  value={String(status?.knowledge_chunks ?? 0)} />
              <InfoBadge label="Rules"  icon="list"      value={String(status?.active_rules ?? 0)} />
              <InfoBadge label="Correx" icon="edit-2"    value={String(status?.total_corrections ?? 0)} />
            </View>
          </Card>

          {/* Rules section */}
          <SectionHeader
            label="Active Rules"
            right={
              <ScalePressable onPress={() => setAddRuleModal(true)}>
                <View style={styles.addBtn}>
                  <Feather name="plus-circle" size={13} color={C.accent} />
                  <Text style={styles.addBtnText}>Add Rule</Text>
                </View>
              </ScalePressable>
            }
          />

          {rules.length === 0 ? (
            <Card style={styles.emptyCard}>
              <Feather name="inbox" size={24} color={C.dim} style={{ marginBottom: S.sm }} />
              <Text style={styles.emptyText}>No rules yet</Text>
              <Text style={styles.emptySub}>Rules are injected into every answer when brain is ON.</Text>
            </Card>
          ) : (
            rules.map((rule) => (
              <Card key={rule.id} style={styles.ruleCard} surface="s2">
                <View style={styles.ruleTop}>
                  <View style={styles.ruleChip}>
                    <Text style={styles.ruleChipText}>{rule.topic}</Text>
                  </View>
                  <Text style={styles.ruleId}>{rule.id}</Text>
                  <ScalePressable onPress={() => removeRule(rule.id)}>
                    <View style={styles.ruleDeleteBtn}>
                      <Feather name="trash-2" size={13} color={C.red} />
                    </View>
                  </ScalePressable>
                </View>
                <Text style={styles.ruleText}>{rule.rule_text}</Text>
                <Text style={styles.ruleDate}>{new Date(rule.created_at).toLocaleDateString()}</Text>
              </Card>
            ))
          )}
        </Animated.View>
      </ScrollView>

      {/* Add Rule Modal */}
      <Modal visible={addRuleModal} transparent animationType="slide">
        <KeyboardAvoidingView style={styles.modalOverlay} behavior={Platform.OS === "ios" ? "padding" : "height"}>
          <Pressable style={styles.modalDismiss} onPress={() => setAddRuleModal(false)} />
          <View style={styles.modalCard}>
            <View style={styles.handle} />
            <Text style={styles.modalTitle}>Add Permanent Rule</Text>
            <Text style={styles.modalHint}>Injected into every LIOS answer when brain is ON.</Text>
            <TextInput
              style={styles.modalInput}
              value={ruleText}
              onChangeText={setRuleText}
              placeholder="e.g. Always cite the EU article number"
              placeholderTextColor={C.dim}
              multiline autoFocus textAlignVertical="top"
            />
            <TextInput
              style={styles.modalInputSmall}
              value={ruleTopic}
              onChangeText={setRuleTopic}
              placeholder="Topic (e.g. CSRD, general)"
              placeholderTextColor={C.dim}
            />
            <View style={styles.modalActions}>
              <ScalePressable onPress={() => setAddRuleModal(false)} style={styles.modalCancel}>
                <Text style={styles.modalCancelText}>Cancel</Text>
              </ScalePressable>
              <ScalePressable
                onPress={addRule}
                disabled={!ruleText.trim()}
                style={[styles.modalSave, !ruleText.trim() && styles.btnDisabled]}
              >
                <Text style={styles.modalSaveText}>Add Rule</Text>
              </ScalePressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* Server URL Modal */}
      <Modal visible={serverUrlModal} transparent animationType="slide">
        <KeyboardAvoidingView style={styles.modalOverlay} behavior={Platform.OS === "ios" ? "padding" : "height"}>
          <Pressable style={styles.modalDismiss} onPress={() => setServerUrlModal(false)} />
          <View style={styles.modalCard}>
            <View style={styles.handle} />
            <View style={styles.modalTitleRow}>
              <Feather name="server" size={16} color={C.accent} />
              <Text style={[styles.modalTitle, { marginLeft: S.sm, marginBottom: 0 }]}>Server URL</Text>
            </View>
            <Text style={styles.modalHint}>Your Mac's LAN IP — same WiFi as phone.</Text>
            <TextInput
              style={styles.modalInput}
              value={urlInput}
              onChangeText={setUrlInput}
              placeholder="http://192.168.1.x:8000"
              placeholderTextColor={C.dim}
              autoCapitalize="none"
              keyboardType="url"
              autoFocus
            />
            <View style={styles.modalActions}>
              <ScalePressable onPress={() => setServerUrlModal(false)} style={styles.modalCancel}>
                <Text style={styles.modalCancelText}>Cancel</Text>
              </ScalePressable>
              <ScalePressable onPress={saveServerUrl} style={styles.modalSave}>
                <Text style={styles.modalSaveText}>Save</Text>
              </ScalePressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: C.bg },
  center:       { flex: 1, alignItems: "center", justifyContent: "center" },
  header:       { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: S.md, paddingVertical: S.sm + 2, borderBottomWidth: 1, borderBottomColor: C.border },
  headerTitle:  { fontSize: F.xl, fontWeight: W.bold, color: C.text },
  serverBtn:    { flexDirection: "row", alignItems: "center", gap: 5, backgroundColor: C.s1, borderRadius: R.full, paddingHorizontal: S.sm + 2, paddingVertical: 5, borderWidth: 1, borderColor: C.border },
  serverBtnText:{ color: C.mid, fontSize: F.xs, fontWeight: W.semi },
  scroll:       { padding: S.md, gap: S.md },

  // Brain card
  brainCard:  { marginBottom: S.xs },
  brainRow:   { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  brainLeft:  { flexDirection: "row", alignItems: "center", flex: 1 },
  cardTitle:  { fontSize: F.lg, fontWeight: W.bold, color: C.text },
  cardSub:    { fontSize: F.sm, color: C.mid, marginTop: 2 },
  divider:    { height: 1, backgroundColor: C.border, marginVertical: S.md },

  // Pill toggle
  pillTrack:  { width: 46, height: 26, borderRadius: R.full, justifyContent: "center" },
  pillThumb:  { width: 22, height: 22, borderRadius: R.full, backgroundColor: C.text, elevation: 2 },

  // Badge grid
  badgeGrid:    { flexDirection: "row", flexWrap: "wrap", gap: S.sm },
  infoBadge:    { backgroundColor: C.bg, borderRadius: R.sm, paddingHorizontal: S.sm + 2, paddingVertical: S.sm, minWidth: 72, alignItems: "center", borderWidth: 1, borderColor: C.border },
  infoBadgeLabel: { fontSize: 9, color: C.dim, textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 2 },
  infoBadgeValue: { fontSize: F.md, fontWeight: W.bold, color: C.text },

  // Rules
  addBtn:     { flexDirection: "row", alignItems: "center", gap: 5, backgroundColor: C.accentDim, borderRadius: R.full, paddingHorizontal: S.sm + 2, paddingVertical: 5, borderWidth: 1, borderColor: C.borderBright },
  addBtnText: { color: C.accent, fontSize: F.xs, fontWeight: W.semi },
  emptyCard:  { alignItems: "center", paddingVertical: S.xl },
  emptyText:  { color: C.mid, fontSize: F.md, fontWeight: W.semi },
  emptySub:   { color: C.dim, fontSize: F.sm, marginTop: S.xs, textAlign: "center" },
  ruleCard:   { marginBottom: S.sm },
  ruleTop:    { flexDirection: "row", alignItems: "center", marginBottom: S.sm, gap: S.sm },
  ruleChip:   { backgroundColor: C.accentDim, borderRadius: R.xs, paddingHorizontal: 7, paddingVertical: 3, borderWidth: 1, borderColor: C.borderBright },
  ruleChipText: { color: C.accent, fontSize: 10, fontWeight: W.semi },
  ruleId:     { flex: 1, color: C.dim, fontSize: F.xs },
  ruleDeleteBtn: { width: 28, height: 28, borderRadius: R.sm, backgroundColor: C.redDim, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: C.red + "44" },
  ruleText:   { fontSize: F.sm, color: C.text, lineHeight: 20 },
  ruleDate:   { fontSize: F.xs, color: C.dim, marginTop: S.xs },

  // Modal
  modalOverlay:  { flex: 1, backgroundColor: "rgba(0,0,0,0.65)", justifyContent: "flex-end" },
  modalDismiss:  { flex: 1 },
  modalCard:     { backgroundColor: C.s3, borderTopLeftRadius: R.lg, borderTopRightRadius: R.lg, padding: S.md, paddingBottom: 36, borderTopWidth: 1, borderColor: C.border },
  handle:        { width: 36, height: 4, backgroundColor: C.border, borderRadius: 2, alignSelf: "center", marginBottom: S.md },
  modalTitleRow: { flexDirection: "row", alignItems: "center", marginBottom: S.sm },
  modalTitle:    { fontSize: F.lg, fontWeight: W.bold, color: C.text, marginBottom: S.xs },
  modalHint:     { fontSize: F.sm, color: C.mid, marginBottom: S.md, lineHeight: 18 },
  modalInput:    { backgroundColor: C.s2, borderRadius: R.md, padding: S.md, color: C.text, fontSize: F.md, minHeight: 80, marginBottom: S.sm, borderWidth: 1, borderColor: C.border },
  modalInputSmall: { backgroundColor: C.s2, borderRadius: R.md, padding: S.md, color: C.text, fontSize: F.md, marginBottom: S.md, borderWidth: 1, borderColor: C.border },
  modalActions:  { flexDirection: "row", gap: S.sm },
  modalCancel:   { flex: 1, padding: S.md, borderRadius: R.md, backgroundColor: C.s2, alignItems: "center" },
  modalCancelText: { color: C.mid, fontWeight: W.semi },
  modalSave:     { flex: 2, padding: S.md, borderRadius: R.md, backgroundColor: C.accent, alignItems: "center" },
  btnDisabled:   { opacity: 0.4 },
  modalSaveText: { color: C.bg, fontWeight: W.bold },
});
