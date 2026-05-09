import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
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
import * as DocumentPicker from "expo-document-picker";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { api, Correction } from "../api/client";
import ScalePressable from "../components/ScalePressable";
import Card from "../components/Card";
import SectionHeader from "../components/SectionHeader";
import { C, F, R, S, W } from "../theme";

const REGULATIONS = [
  "CSRD", "ESRS", "EU-Taxonomie", "SFDR", "CS3D",
  "GDPR", "BGB", "StGB", "LKSG", "EUDR", "CUSTOM",
];

const HISTORY_KEY = "lios_upload_history";

interface UploadRecord {
  id: string;
  filename: string;
  regulation: string;
  chunks: number;
  ts: number;
}

function RegPill({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  return (
    <Pressable onPress={onPress}>
      <View style={[up.pill, selected && up.pillActive]}>
        <Text style={[up.pillText, selected && up.pillTextActive]}>{label}</Text>
      </View>
    </Pressable>
  );
}

export default function UploadScreen({ onClose }: { onClose?: () => void }) {
  const [file, setFile]               = useState<{ name: string; uri: string; type: string } | null>(null);
  const [title, setTitle]             = useState("");
  const [regulation, setRegulation]   = useState("CUSTOM");
  const [uploading, setUploading]     = useState(false);
  const [result, setResult]           = useState<{ ok: boolean; chunks: number; msg: string } | null>(null);
  const [history, setHistory]         = useState<UploadRecord[]>([]);
  const [corrections, setCorrections] = useState<Correction[]>([]);
  const [loadingCorr, setLoadingCorr] = useState(false);
  const [refreshing, setRefreshing]   = useState(false);
  const mountAnim = useRef(new Animated.Value(0)).current;
  const resultAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(mountAnim, { toValue: 1, duration: 280, useNativeDriver: true }).start();
    loadHistory();
    loadCorrections();
  }, []);

  const loadHistory = async () => {
    const raw = await AsyncStorage.getItem(HISTORY_KEY);
    if (raw) setHistory(JSON.parse(raw));
  };

  const saveHistory = async (record: UploadRecord) => {
    const updated = [record, ...history].slice(0, 20);
    setHistory(updated);
    await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
  };

  const loadCorrections = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true); else setLoadingCorr(true);
    try {
      const res = await api.upload.corrections(30);
      setCorrections(res.corrections);
    } catch {}
    finally { setLoadingCorr(false); setRefreshing(false); }
  }, []);

  const pickFile = async () => {
    const res = await DocumentPicker.getDocumentAsync({
      type: ["application/pdf", "text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
      copyToCacheDirectory: true,
    });
    if (res.canceled || !res.assets?.length) return;
    const asset = res.assets[0];
    setFile({ name: asset.name, uri: asset.uri, type: asset.mimeType ?? "application/octet-stream" });
    setResult(null);
    if (!title) setTitle(asset.name.replace(/\.[^.]+$/, ""));
  };

  const upload = useCallback(async () => {
    if (!file || uploading) return;
    setUploading(true);
    setResult(null);
    try {
      const form = new FormData();
      form.append("file", { uri: file.uri, name: file.name, type: file.type } as any);
      form.append("title", title || file.name);
      form.append("regulation", regulation);

      const res = await api.upload.document(form);
      const record: UploadRecord = {
        id: `up-${Date.now()}`,
        filename: file.name,
        regulation,
        chunks: res.chunks_added,
        ts: Date.now(),
      };
      await saveHistory(record);
      setResult({ ok: true, chunks: res.chunks_added, msg: `${res.chunks_added} Abschnitte hinzugefügt` });
      setFile(null);
      setTitle("");
      resultAnim.setValue(0);
      Animated.spring(resultAnim, { toValue: 1, useNativeDriver: true, speed: 16, bounciness: 5 }).start();
    } catch (e: any) {
      setResult({ ok: false, chunks: 0, msg: e?.message ?? "Upload fehlgeschlagen" });
    } finally {
      setUploading(false);
    }
  }, [file, title, regulation, uploading, history, resultAnim]);

  return (
    <SafeAreaView style={up.root} edges={["top"]}>
      <View style={up.header}>
        <View style={up.headerLeft}>
          {onClose && (
            <Pressable onPress={onClose} style={up.closeBtn}>
              <Feather name="x" size={20} color={C.mid} />
            </Pressable>
          )}
          <Text style={up.headerTitle}>Trainieren</Text>
        </View>
        <View style={up.headerBadge}>
          <Feather name="database" size={12} color={C.primary} />
          <Text style={up.headerBadgeText}>{history.length} hochgeladen</Text>
        </View>
      </View>

      <ScrollView
        contentContainerStyle={up.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => loadCorrections(true)} tintColor={C.primary} />}
      >
        <Animated.View style={{ opacity: mountAnim }}>

          {/* Upload card */}
          <Card accent>
            <View style={up.cardTitleRow}>
              <View style={up.cardIcon}>
                <Feather name="upload" size={15} color={C.primary} />
              </View>
              <Text style={up.cardTitle}>Dokument hochladen</Text>
            </View>
            <Text style={up.cardSub}>PDF, TXT oder DOCX — wird direkt in die Wissensbasis indexiert</Text>

            {/* File picker */}
            <ScalePressable onPress={pickFile}>
              <View style={[up.filePicker, file && up.filePickerActive]}>
                {file ? (
                  <View style={up.fileInfo}>
                    <View style={up.fileIcon}>
                      <Feather name="file-text" size={16} color={C.primary} />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={up.fileName} numberOfLines={1}>{file.name}</Text>
                      <Text style={up.fileType}>{file.type}</Text>
                    </View>
                    <Pressable onPress={() => { setFile(null); setTitle(""); setResult(null); }}>
                      <Feather name="x" size={16} color={C.mid} />
                    </Pressable>
                  </View>
                ) : (
                  <View style={up.fileEmpty}>
                    <Feather name="upload-cloud" size={24} color={C.dim} />
                    <Text style={up.fileEmptyText}>Datei auswählen</Text>
                    <Text style={up.fileEmptyHint}>PDF · TXT · DOCX</Text>
                  </View>
                )}
              </View>
            </ScalePressable>

            {/* Title input */}
            <TextInput
              style={up.input}
              value={title}
              onChangeText={setTitle}
              placeholder="Titel (optional)"
              placeholderTextColor={C.dim}
            />

            {/* Regulation picker */}
            <Text style={up.label}>REGULIERUNG / THEMA</Text>
            <View style={up.pills}>
              {REGULATIONS.map((r) => (
                <RegPill key={r} label={r} selected={regulation === r} onPress={() => setRegulation(r)} />
              ))}
            </View>

            {/* Upload button */}
            <ScalePressable onPress={upload} disabled={!file || uploading}>
              <View style={[up.uploadBtn, (!file || uploading) && up.uploadBtnOff]}>
                {uploading
                  ? <ActivityIndicator size="small" color={C.card} />
                  : <><Feather name="upload" size={15} color={C.card} /><Text style={up.uploadBtnText}>Jetzt hochladen & indexieren</Text></>
                }
              </View>
            </ScalePressable>

            {/* Result */}
            {result && (
              <Animated.View style={[up.result, result.ok ? up.resultOk : up.resultErr, { opacity: resultAnim, transform: [{ scale: resultAnim.interpolate({ inputRange: [0, 1], outputRange: [0.95, 1] }) }] }]}>
                <Feather name={result.ok ? "check-circle" : "alert-circle"} size={14} color={result.ok ? C.green : C.red} />
                <Text style={[up.resultText, { color: result.ok ? C.green : C.red }]}>{result.msg}</Text>
              </Animated.View>
            )}
          </Card>

          {/* Upload history */}
          {history.length > 0 && (
            <>
              <SectionHeader label="Hochgeladene Dokumente" />
              {history.map((rec) => (
                <Card key={rec.id} style={up.histRow} surface="s2">
                  <View style={up.histTop}>
                    <View style={up.histIcon}>
                      <Feather name="file-text" size={13} color={C.primary} />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={up.histName} numberOfLines={1}>{rec.filename}</Text>
                      <Text style={up.histMeta}>{rec.regulation} · {rec.chunks} Abschnitte · {new Date(rec.ts).toLocaleDateString("de-DE")}</Text>
                    </View>
                    <View style={up.histBadge}>
                      <Text style={up.histBadgeText}>+{rec.chunks}</Text>
                    </View>
                  </View>
                </Card>
              ))}
            </>
          )}

          {/* Recent corrections */}
          <SectionHeader
            label="Letzte Korrekturen"
            right={
              loadingCorr
                ? <ActivityIndicator size="small" color={C.primary} />
                : <ScalePressable onPress={() => loadCorrections(true)}>
                    <Feather name="refresh-cw" size={13} color={C.mid} />
                  </ScalePressable>
            }
          />

          {corrections.length === 0 && !loadingCorr ? (
            <Card style={up.emptyCard}>
              <Feather name="message-circle" size={20} color={C.dim} style={{ marginBottom: S.xs }} />
              <Text style={up.emptyText}>Noch keine Korrekturen</Text>
              <Text style={up.emptySub}>Geben Sie im Chat-Tab Feedback auf Antworten — sie erscheinen hier.</Text>
            </Card>
          ) : (
            corrections.map((c) => (
              <Card key={c.id} style={up.corrCard} surface="s2">
                <View style={up.corrTop}>
                  <View style={[up.corrTypeBadge, c.feedback_type === "wrong" ? up.corrTypeBad : up.corrTypePartial]}>
                    <Text style={[up.corrTypeText, { color: c.feedback_type === "wrong" ? C.red : C.amber }]}>
                      {c.feedback_type === "wrong" ? "Falsch" : "Ergänzung"}
                    </Text>
                  </View>
                  <Text style={up.corrDate}>{new Date(c.created_at).toLocaleDateString("de-DE")}</Text>
                </View>
                <Text style={up.corrQuery} numberOfLines={2}>{c.user_query}</Text>
                <View style={up.corrDivider} />
                <Text style={up.corrText}>{c.correction_text}</Text>
              </Card>
            ))
          )}

        </Animated.View>
      </ScrollView>
    </SafeAreaView>
  );
}

const up = StyleSheet.create({
  root:   { flex: 1, backgroundColor: C.bg },
  scroll: { padding: S.md, gap: S.md },

  header:          { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: S.md, paddingVertical: S.sm + 2, backgroundColor: C.card, borderBottomWidth: 1, borderBottomColor: C.border },
  headerLeft:      { flexDirection: "row", alignItems: "center", gap: S.sm },
  closeBtn:        { width: 32, height: 32, borderRadius: R.sm, alignItems: "center", justifyContent: "center", backgroundColor: C.s2, borderWidth: 1, borderColor: C.border },
  headerTitle:     { fontSize: F.xl, fontWeight: W.bold, color: C.text },
  headerBadge:     { flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: C.primaryDim, borderRadius: R.full, paddingHorizontal: S.sm + 2, paddingVertical: 5 },
  headerBadgeText: { fontSize: F.xs, color: C.primary, fontWeight: W.semi },

  cardTitleRow:    { flexDirection: "row", alignItems: "center", gap: S.sm, marginBottom: S.xs },
  cardIcon:        { width: 30, height: 30, borderRadius: R.sm, backgroundColor: C.primaryDim, alignItems: "center", justifyContent: "center" },
  cardTitle:       { fontSize: F.md, fontWeight: W.bold, color: C.text },
  cardSub:         { fontSize: F.xs, color: C.mid, marginBottom: S.md, lineHeight: 18 },

  filePicker:      { borderWidth: 1.5, borderColor: C.border, borderStyle: "dashed", borderRadius: R.md, padding: S.md, marginBottom: S.sm },
  filePickerActive:{ borderColor: C.primary, borderStyle: "solid", backgroundColor: C.primaryDim },
  fileEmpty:       { alignItems: "center", gap: S.xs, paddingVertical: S.sm },
  fileEmptyText:   { fontSize: F.sm, color: C.mid, fontWeight: W.semi },
  fileEmptyHint:   { fontSize: F.xs, color: C.dim },
  fileInfo:        { flexDirection: "row", alignItems: "center", gap: S.sm },
  fileIcon:        { width: 32, height: 32, borderRadius: R.sm, backgroundColor: C.card, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: C.border },
  fileName:        { fontSize: F.sm, fontWeight: W.semi, color: C.text },
  fileType:        { fontSize: F.xs, color: C.dim, marginTop: 2 },

  input:           { backgroundColor: C.bg, borderRadius: R.sm, borderWidth: 1, borderColor: C.border, paddingHorizontal: S.md, paddingVertical: S.sm + 2, color: C.text, fontSize: F.md, marginBottom: S.sm },
  label:           { fontSize: 10, fontWeight: W.bold, color: C.dim, letterSpacing: 1.2, marginBottom: S.sm },
  pills:           { flexDirection: "row", flexWrap: "wrap", gap: S.xs, marginBottom: S.md },
  pill:            { paddingHorizontal: S.sm + 2, paddingVertical: 5, borderRadius: R.full, borderWidth: 1, borderColor: C.border, backgroundColor: C.card },
  pillActive:      { backgroundColor: C.primary, borderColor: C.primary },
  pillText:        { fontSize: F.xs, color: C.mid, fontWeight: W.medium },
  pillTextActive:  { color: C.card, fontWeight: W.semi },

  uploadBtn:       { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: S.sm, backgroundColor: C.primary, borderRadius: R.md, paddingVertical: S.sm + 4 },
  uploadBtnOff:    { opacity: 0.4 },
  uploadBtnText:   { color: C.card, fontWeight: W.bold, fontSize: F.md },

  result:          { flexDirection: "row", alignItems: "center", gap: S.sm, marginTop: S.sm, borderRadius: R.sm, padding: S.sm + 2 },
  resultOk:        { backgroundColor: C.greenBg },
  resultErr:       { backgroundColor: C.redBg },
  resultText:      { fontSize: F.sm, fontWeight: W.semi, flex: 1 },

  // Upload history
  histRow:         { marginBottom: S.xs },
  histTop:         { flexDirection: "row", alignItems: "center", gap: S.sm },
  histIcon:        { width: 28, height: 28, borderRadius: R.xs, backgroundColor: C.primaryDim, alignItems: "center", justifyContent: "center" },
  histName:        { fontSize: F.sm, fontWeight: W.semi, color: C.text },
  histMeta:        { fontSize: F.xs, color: C.dim, marginTop: 2 },
  histBadge:       { backgroundColor: C.greenBg, borderRadius: R.xs, paddingHorizontal: 7, paddingVertical: 3 },
  histBadgeText:   { fontSize: 10, color: C.green, fontWeight: W.bold },

  // Corrections
  emptyCard:       { alignItems: "center", paddingVertical: S.lg },
  emptyText:       { fontSize: F.md, color: C.mid, fontWeight: W.semi },
  emptySub:        { fontSize: F.xs, color: C.dim, textAlign: "center", marginTop: S.xs, lineHeight: 18 },
  corrCard:        { marginBottom: S.xs },
  corrTop:         { flexDirection: "row", alignItems: "center", gap: S.sm, marginBottom: S.xs },
  corrTypeBadge:   { borderRadius: R.xs, paddingHorizontal: 7, paddingVertical: 3 },
  corrTypeBad:     { backgroundColor: C.redBg },
  corrTypePartial: { backgroundColor: C.amberBg },
  corrTypeText:    { fontSize: 10, fontWeight: W.semi },
  corrDate:        { fontSize: F.xs, color: C.dim, marginLeft: "auto" as any },
  corrQuery:       { fontSize: F.xs, color: C.mid, lineHeight: 17, marginBottom: S.xs },
  corrDivider:     { height: 1, backgroundColor: C.border, marginBottom: S.xs },
  corrText:        { fontSize: F.sm, color: C.text, lineHeight: 19 },
});
