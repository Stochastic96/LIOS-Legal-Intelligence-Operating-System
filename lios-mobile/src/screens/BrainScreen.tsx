import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { api, BrainStatus, Rule, getServerUrl, setServerUrl } from "../api/client";

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
      setRuleText("");
      setRuleTopic("general");
      setAddRuleModal(false);
    } catch {
      Alert.alert("Error", "Could not add rule.");
    }
  }, [ruleText, ruleTopic]);

  const removeRule = useCallback(async (id: string) => {
    Alert.alert("Remove Rule", "Deactivate this rule?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Remove",
        style: "destructive",
        onPress: async () => {
          try {
            await api.memory.deleteRule(id);
            setRules((prev) => prev.filter((r) => r.id !== id));
          } catch {}
        },
      },
    ]);
  }, []);

  const saveServerUrl = useCallback(async () => {
    await setServerUrl(urlInput.trim());
    setServerUrlModal(false);
    loadAll();
  }, [urlInput, loadAll]);

  const openServerUrl = useCallback(async () => {
    const current = await getServerUrl();
    setUrlInput(current);
    setServerUrlModal(true);
  }, []);

  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={["top"]}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#6366f1" />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Brain</Text>
        <Pressable onPress={openServerUrl} style={styles.serverBtn}>
          <Text style={styles.serverBtnText}>⚙ Server</Text>
        </Pressable>
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => loadAll(true)} tintColor="#6366f1" />}
      >
        {/* Brain toggle card */}
        <View style={styles.card}>
          <View style={styles.cardRow}>
            <View>
              <Text style={styles.cardTitle}>🧠 Brain</Text>
              <Text style={styles.cardSub}>
                {status?.brain_on ? "LLM-powered answers active" : "Rule-based fallback only"}
              </Text>
            </View>
            <Switch
              value={status?.brain_on ?? false}
              onValueChange={toggleBrain}
              disabled={toggling}
              trackColor={{ false: "#334155", true: "#6366f1" }}
              thumbColor="#fff"
            />
          </View>

          <View style={styles.divider} />

          <View style={styles.infoRow}>
            <InfoBadge label="Model" value={status?.model ?? "—"} />
            <InfoBadge label="LLM" value={status?.llm_reachable ? "✅ Online" : "❌ Offline"} valueColor={status?.llm_reachable ? "#22c55e" : "#ef4444"} />
            <InfoBadge label="Chunks" value={String(status?.knowledge_chunks ?? 0)} />
          </View>
          <View style={[styles.infoRow, { marginTop: 8 }]}>
            <InfoBadge label="Corrections" value={String(status?.total_corrections ?? 0)} />
            <InfoBadge label="Active Rules" value={String(status?.active_rules ?? 0)} />
          </View>
        </View>

        {/* Rules section */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Active Rules</Text>
          <Pressable style={styles.addBtn} onPress={() => setAddRuleModal(true)}>
            <Text style={styles.addBtnText}>+ Add Rule</Text>
          </Pressable>
        </View>

        {rules.length === 0 ? (
          <View style={styles.emptyRules}>
            <Text style={styles.emptyRulesText}>No rules yet.</Text>
            <Text style={styles.emptyRulesSub}>Rules are injected into every LIOS answer when brain is ON.</Text>
          </View>
        ) : (
          rules.map((rule) => (
            <View key={rule.id} style={styles.ruleCard}>
              <View style={styles.ruleTop}>
                <View style={styles.ruleTopicChip}>
                  <Text style={styles.ruleTopicText}>{rule.topic}</Text>
                </View>
                <Text style={styles.ruleId}>{rule.id}</Text>
                <Pressable onPress={() => removeRule(rule.id)} style={styles.ruleDelete}>
                  <Text style={styles.ruleDeleteText}>✕</Text>
                </Pressable>
              </View>
              <Text style={styles.ruleText}>{rule.rule_text}</Text>
              <Text style={styles.ruleDate}>{new Date(rule.created_at).toLocaleDateString()}</Text>
            </View>
          ))
        )}
      </ScrollView>

      {/* Add Rule Modal */}
      <Modal visible={addRuleModal} transparent={true} animationType="slide">
        <KeyboardAvoidingView
          style={styles.modalOverlay}
          behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
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
              placeholderTextColor="#475569"
              multiline={true}
              autoFocus={true}
              textAlignVertical="top"
            />
            <TextInput
              style={styles.modalInputSmall}
              value={ruleTopic}
              onChangeText={setRuleTopic}
              placeholder="Topic (e.g. CSRD, general)"
              placeholderTextColor="#475569"
            />
            <View style={styles.modalActions}>
              <Pressable style={styles.modalCancel} onPress={() => setAddRuleModal(false)}>
                <Text style={styles.modalCancelText}>Cancel</Text>
              </Pressable>
              <Pressable style={[styles.modalSave, !ruleText.trim() && styles.btnDisabled]} onPress={addRule} disabled={!ruleText.trim()}>
                <Text style={styles.modalSaveText}>Add Rule</Text>
              </Pressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* Server URL Modal */}
      <Modal visible={serverUrlModal} transparent={true} animationType="slide">
        <KeyboardAvoidingView
          style={styles.modalOverlay}
          behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
          <Pressable style={styles.modalDismiss} onPress={() => setServerUrlModal(false)} />
          <View style={styles.modalCard}>
            <View style={styles.handle} />
            <Text style={styles.modalTitle}>Server URL</Text>
            <Text style={styles.modalHint}>Your Mac's LAN IP — same WiFi as phone.</Text>
            <TextInput
              style={styles.modalInput}
              value={urlInput}
              onChangeText={setUrlInput}
              placeholder="http://192.168.1.x:8000"
              placeholderTextColor="#475569"
              autoCapitalize="none"
              keyboardType="url"
              autoFocus={true}
            />
            <View style={styles.modalActions}>
              <Pressable style={styles.modalCancel} onPress={() => setServerUrlModal(false)}>
                <Text style={styles.modalCancelText}>Cancel</Text>
              </Pressable>
              <Pressable style={styles.modalSave} onPress={saveServerUrl}>
                <Text style={styles.modalSaveText}>Save</Text>
              </Pressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

function InfoBadge({ label, value, valueColor }: { label: string; value: string; valueColor?: string }) {
  return (
    <View style={infoBadgeStyles.badge}>
      <Text style={infoBadgeStyles.label}>{label}</Text>
      <Text style={[infoBadgeStyles.value, valueColor ? { color: valueColor } : {}]}>{value}</Text>
    </View>
  );
}

const infoBadgeStyles = StyleSheet.create({
  badge: { backgroundColor: "#0f172a", borderRadius: 10, paddingHorizontal: 12, paddingVertical: 8, minWidth: 80 },
  label: { fontSize: 10, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 2 },
  value: { fontSize: 14, fontWeight: "700", color: "#e2e8f0" },
});

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "#1e293b" },
  headerTitle: { fontSize: 20, fontWeight: "700", color: "#e2e8f0" },
  serverBtn: { backgroundColor: "#1e293b", borderRadius: 20, paddingHorizontal: 12, paddingVertical: 4 },
  serverBtnText: { color: "#94a3b8", fontSize: 12, fontWeight: "600" },
  scroll: { padding: 16 },
  card: { backgroundColor: "#1e293b", borderRadius: 16, padding: 16, marginBottom: 20 },
  cardRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  cardTitle: { fontSize: 17, fontWeight: "700", color: "#e2e8f0" },
  cardSub: { fontSize: 13, color: "#64748b", marginTop: 2 },
  divider: { height: 1, backgroundColor: "#0f172a", marginVertical: 14 },
  infoRow: { flexDirection: "row", gap: 8 },
  sectionHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 12 },
  sectionTitle: { fontSize: 15, fontWeight: "700", color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5 },
  addBtn: { backgroundColor: "#312e81", borderRadius: 20, paddingHorizontal: 12, paddingVertical: 4 },
  addBtnText: { color: "#a5b4fc", fontSize: 12, fontWeight: "600" },
  emptyRules: { backgroundColor: "#1e293b", borderRadius: 12, padding: 20, alignItems: "center" },
  emptyRulesText: { color: "#64748b", fontSize: 14, fontWeight: "600" },
  emptyRulesSub: { color: "#334155", fontSize: 12, marginTop: 6, textAlign: "center" },
  ruleCard: { backgroundColor: "#1e293b", borderRadius: 12, padding: 14, marginBottom: 8 },
  ruleTop: { flexDirection: "row", alignItems: "center", marginBottom: 8, gap: 8 },
  ruleTopicChip: { backgroundColor: "#312e81", borderRadius: 10, paddingHorizontal: 8, paddingVertical: 3 },
  ruleTopicText: { color: "#a5b4fc", fontSize: 11, fontWeight: "600" },
  ruleId: { flex: 1, color: "#475569", fontSize: 11 },
  ruleDelete: { width: 24, height: 24, borderRadius: 12, backgroundColor: "#7f1d1d", alignItems: "center", justifyContent: "center" },
  ruleDeleteText: { color: "#fca5a5", fontSize: 11, fontWeight: "700" },
  ruleText: { fontSize: 14, color: "#e2e8f0", lineHeight: 20 },
  ruleDate: { fontSize: 11, color: "#475569", marginTop: 6 },
  // Modal
  modalOverlay: { flex: 1, backgroundColor: "rgba(0,0,0,0.6)", justifyContent: "flex-end" },
  modalDismiss: { flex: 1 },
  modalCard: {
    backgroundColor: "#1e293b",
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 20,
    paddingBottom: 36,
  },
  handle: { width: 36, height: 4, backgroundColor: "#334155", borderRadius: 2, alignSelf: "center", marginBottom: 16 },
  modalTitle: { fontSize: 17, fontWeight: "700", color: "#e2e8f0", marginBottom: 4 },
  modalHint: { fontSize: 13, color: "#64748b", marginBottom: 14, lineHeight: 18 },
  modalInput: {
    backgroundColor: "#0f172a",
    borderRadius: 12,
    padding: 14,
    color: "#e2e8f0",
    fontSize: 15,
    minHeight: 80,
    marginBottom: 10,
  },
  modalInputSmall: { backgroundColor: "#0f172a", borderRadius: 12, padding: 14, color: "#e2e8f0", fontSize: 15, marginBottom: 16 },
  modalActions: { flexDirection: "row", gap: 10 },
  modalCancel: { flex: 1, padding: 14, borderRadius: 12, backgroundColor: "#0f172a", alignItems: "center" },
  modalCancelText: { color: "#64748b", fontWeight: "600" },
  modalSave: { flex: 2, padding: 14, borderRadius: 12, backgroundColor: "#6366f1", alignItems: "center" },
  btnDisabled: { opacity: 0.4 },
  modalSaveText: { color: "#fff", fontWeight: "700" },
});
