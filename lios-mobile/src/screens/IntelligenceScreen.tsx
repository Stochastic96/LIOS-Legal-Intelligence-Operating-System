import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  Linking,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Feather } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import {
  api,
  AnswerRecord,
  CorpusFileRecord,
  CorpusRegulation,
  IntelligenceStats,
  TopicCoverage,
} from "../api/client";
import { C, F, R, S, W } from "../theme";

// ── Status helpers ─────────────────────────────────────────────────────────────

const STATUS_COLOR: Record<string, string> = {
  mastered:   "#10B981",
  functional: "#3B82F6",
  connected:  "#8B5CF6",
  learning:   "#F59E0B",
  seed:       "#6B7280",
  unknown:    "#9CA3AF",
};

function pctBg(status: string): string {
  return STATUS_COLOR[status] ?? C.dim;
}

// ── KPI tile ──────────────────────────────────────────────────────────────────

function KpiTile({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <View style={s.kpiTile}>
      <Text style={s.kpiValue}>{value}</Text>
      <Text style={s.kpiLabel}>{label}</Text>
      {sub ? <Text style={s.kpiSub}>{sub}</Text> : null}
    </View>
  );
}

// ── Section header ─────────────────────────────────────────────────────────────

function SectionHdr({ title }: { title: string }) {
  return (
    <View style={s.sectionHdr}>
      <Text style={s.sectionHdrText}>{title}</Text>
      <View style={s.sectionLine} />
    </View>
  );
}

// ── Expandable corpus row ─────────────────────────────────────────────────────

function CorpusRow({ reg }: { reg: CorpusRegulation }) {
  const [open, setOpen] = useState(false);
  const anim = useRef(new Animated.Value(0)).current;

  function toggle() {
    Animated.timing(anim, {
      toValue: open ? 0 : 1,
      duration: 220,
      useNativeDriver: false,
    }).start();
    setOpen(!open);
  }

  return (
    <View style={s.corpusRow}>
      <Pressable style={s.corpusHeader} onPress={toggle}>
        <View style={s.corpusHeaderLeft}>
          <Feather
            name={open ? "chevron-down" : "chevron-right"}
            size={14}
            color={C.mid}
          />
          <Text style={s.corpusName}>{reg.regulation}</Text>
          <View style={[s.corpusBadge, { backgroundColor: C.surface }]}>
            <Text style={s.corpusBadgeText}>{reg.chunk_count}</Text>
          </View>
        </View>
        <Text style={s.corpusArtCount}>{reg.article_count} Art.</Text>
      </Pressable>

      {open && (
        <View style={s.corpusDetails}>
          {reg.celex_id ? (
            <Text style={s.corpusDetailLine}>CELEX: {reg.celex_id}</Text>
          ) : null}
          {reg.published_date ? (
            <Text style={s.corpusDetailLine}>Veröffentlicht: {reg.published_date}</Text>
          ) : null}
          {reg.source_url ? (
            <Pressable onPress={() => Linking.openURL(reg.source_url)}>
              <Text style={[s.corpusDetailLine, s.link]} numberOfLines={1}>
                {reg.source_url}
              </Text>
            </Pressable>
          ) : null}
          {reg.articles.length > 0 && (
            <Text style={s.corpusDetailLine} numberOfLines={3}>
              Artikel: {reg.articles.slice(0, 10).join(", ")}
              {reg.articles.length > 10 ? ` … +${reg.articles.length - 10}` : ""}
            </Text>
          )}
        </View>
      )}
    </View>
  );
}

// ── Category coverage group ───────────────────────────────────────────────────

function CategoryGroup({ cat, topics }: { cat: string; topics: TopicCoverage[] }) {
  const [open, setOpen] = useState(true);
  const avg = topics.length
    ? Math.round(topics.reduce((a, t) => a + t.pct, 0) / topics.length)
    : 0;

  return (
    <View style={s.catGroup}>
      <Pressable style={s.catHeader} onPress={() => setOpen(!open)}>
        <View style={s.catHeaderLeft}>
          <Feather name={open ? "chevron-down" : "chevron-right"} size={14} color={C.mid} />
          <Text style={s.catName}>{cat}</Text>
        </View>
        <Text style={s.catAvg}>{avg}%</Text>
      </Pressable>

      {open &&
        topics.map((t) => (
          <View key={t.id} style={s.topicRow}>
            <View style={[s.topicDot, { backgroundColor: pctBg(t.status) }]} />
            <Text style={s.topicName} numberOfLines={1}>{t.name}</Text>
            <View style={s.topicBarWrap}>
              <View style={[s.topicBarFill, { width: `${t.pct}%` as any, backgroundColor: pctBg(t.status) }]} />
            </View>
            <Text style={[s.topicPct, { color: pctBg(t.status) }]}>{t.pct}%</Text>
            {t.questions_in_bank > 0 && (
              <Text style={s.topicQ}>{t.questions_in_bank}F</Text>
            )}
          </View>
        ))}
    </View>
  );
}

// ── Answer card ────────────────────────────────────────────────────────────────

function AnswerCard({ a }: { a: AnswerRecord }) {
  const [open, setOpen] = useState(false);
  const ts = a.ts ? new Date(a.ts).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" }) : "";
  return (
    <Pressable style={s.ansCard} onPress={() => setOpen(!open)}>
      <View style={s.ansHeader}>
        <Text style={s.ansTopicName}>{a.topic_name}</Text>
        <View style={s.ansRight}>
          {a.valid
            ? <Feather name="check-circle" size={13} color="#10B981" />
            : <Feather name="alert-circle" size={13} color="#EF4444" />}
          <Text style={s.ansTs}>{ts}</Text>
          <Text style={[s.ansDelta, { color: a.pct_after >= a.pct_before ? "#10B981" : "#EF4444" }]}>
            {a.pct_before}%→{a.pct_after}%
          </Text>
        </View>
      </View>
      <Text style={s.ansQ} numberOfLines={open ? undefined : 2}>{a.question}</Text>
      {open && (
        <>
          <View style={s.ansDivider} />
          <Text style={s.ansLabel}>Ihre Antwort</Text>
          <Text style={s.ansText}>{a.user_answer || "—"}</Text>
          {a.corpus_hint ? (
            <>
              <Text style={s.ansLabel}>Corpus-Referenz</Text>
              <Text style={[s.ansText, s.corpusHint]} numberOfLines={6}>{a.corpus_hint}</Text>
            </>
          ) : null}
        </>
      )}
    </Pressable>
  );
}

function FileRow({ file }: { file: CorpusFileRecord }) {
  return (
    <View style={s.fileRow}>
      <View style={{ flex: 1 }}>
        <Text style={s.fileName}>{file.filename}</Text>
        <Text style={s.fileMeta}>
          {file.regulation} · {file.chunk_count} Chunks · {file.article_count} Artikel
        </Text>
      </View>
      {file.source_url ? (
        <Pressable onPress={() => Linking.openURL(file.source_url)}>
          <Feather name="external-link" size={14} color={C.primary} />
        </Pressable>
      ) : null}
    </View>
  );
}

// ── Main screen ────────────────────────────────────────────────────────────────

export default function IntelligenceScreen() {
  const insets = useSafeAreaInsets();

  const [loading, setLoading]   = useState(true);
  const [refreshing, setRefresh] = useState(false);
  const [stats, setStats]       = useState<IntelligenceStats | null>(null);
  const [corpus, setCorpus]     = useState<CorpusRegulation[]>([]);
  const [topics, setTopics]     = useState<TopicCoverage[]>([]);
  const [answers, setAnswers]   = useState<AnswerRecord[]>([]);
  const [files, setFiles]       = useState<CorpusFileRecord[]>([]);
  const [fileQuery, setFileQuery] = useState("");
  const [error, setError]       = useState<string | null>(null);

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefresh(true); else setLoading(true);
    setError(null);
    try {
      const [st, co, to, an, fi] = await Promise.all([
        api.intelligence.stats(),
        api.intelligence.corpus(),
        api.intelligence.topics(),
        api.intelligence.answers(20),
        api.intelligence.files("", 20),
      ]);
      setStats(st);
      setCorpus(co);
      setTopics(to);
      setAnswers(an.answers);
      setFiles(fi.files);
    } catch (e: any) {
      setError(e?.message ?? "Verbindungsfehler");
    } finally {
      setLoading(false);
      setRefresh(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const handle = setTimeout(() => {
      api.intelligence.files(fileQuery, 30)
        .then((response) => setFiles(response.files))
        .catch(() => setFiles([]));
    }, 180);
    return () => clearTimeout(handle);
  }, [fileQuery]);

  // Group topics by category
  const byCategory = topics.reduce<Record<string, TopicCoverage[]>>((acc, t) => {
    const c = t.category || "Sonstige";
    (acc[c] = acc[c] || []).push(t);
    return acc;
  }, {});

  const corpusPct = stats ? Math.min(100, stats.corpus_completeness_pct) : 0;

  if (loading) {
    return (
      <View style={[s.center, { paddingTop: insets.top }]}>
        <ActivityIndicator size="large" color={C.primary} />
        <Text style={s.loadingText}>Lade Intelligenz-Daten …</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={[s.root, { paddingTop: insets.top }]}
      contentContainerStyle={s.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={() => load(true)} tintColor={C.primary} />
      }
    >
      {/* Header */}
      <View style={s.header}>
        <Text style={s.title}>Intelligenz</Text>
        <Pressable onPress={() => load(true)} style={s.refreshBtn}>
          <Feather name="refresh-cw" size={18} color={C.primary} />
        </Pressable>
      </View>

      {error && (
        <View style={s.errorBox}>
          <Feather name="wifi-off" size={14} color="#EF4444" />
          <Text style={s.errorText}>{error}</Text>
        </View>
      )}

      {/* KPI tiles */}
      {stats && (
        <View style={s.kpiRow}>
          <KpiTile label="Chunks" value={stats.total_chunks.toLocaleString()} />
          <KpiTile label="Regelwerke" value={stats.total_regulations} />
          <KpiTile label="Dateien" value={stats.consumed_files} />
          <KpiTile label="Themen" value={stats.total_topics} />
        </View>
      )}

      {/* Corpus progress toward 1M questions */}
      {stats && (
        <View style={s.progressCard}>
          <View style={s.progressLabelRow}>
            <Text style={s.progressLabel}>Fortschritt zum 1-Mio-Ziel</Text>
            <Text style={s.progressPct}>{stats.corpus_completeness_pct}%</Text>
          </View>
          <View style={s.progressTrack}>
            <View style={[s.progressFill, { width: `${corpusPct}%` as any }]} />
          </View>
          <Text style={s.progressSub}>
            {stats.total_chunks.toLocaleString()} / {stats.target_chunks.toLocaleString()} Chunks
            · Ziel: {(stats.target_questions / 1_000_000).toFixed(0)} Mio. Fragen
          </Text>
        </View>
      )}

      {/* Corpus breakdown */}
      {corpus.length > 0 && (
        <>
          <SectionHdr title="WISSENSBASIS" />
          <View style={s.card}>
            {corpus.map((reg) => (
              <CorpusRow key={reg.regulation} reg={reg} />
            ))}
          </View>
        </>
      )}

      <SectionHdr title="KONSUMIERTE INFORMATION" />
      <View style={s.card}>
        <View style={s.searchWrap}>
          <Feather name="search" size={15} color={C.dim} />
          <TextInput
            style={s.searchInput}
            value={fileQuery}
            onChangeText={setFileQuery}
            placeholder="Dateiname suchen, z. B. CSRD oder Francovich"
            placeholderTextColor={C.dim}
            autoCapitalize="none"
            autoCorrect={false}
          />
        </View>
        {files.length > 0 ? (
          files.map((file) => (
            <FileRow key={`${file.filename}-${file.regulation}`} file={file} />
          ))
        ) : (
          <Text style={s.fileEmpty}>
            {fileQuery.trim() ? "Keine Dateinamen passend zur Suche gefunden." : "Noch keine Corpus-Dateien sichtbar."}
          </Text>
        )}
      </View>

      {/* Topic coverage */}
      {Object.keys(byCategory).length > 0 && (
        <>
          <SectionHdr title="THEMENABDECKUNG" />
          <View style={s.card}>
            {Object.entries(byCategory).map(([cat, ts]) => (
              <CategoryGroup key={cat} cat={cat} topics={ts} />
            ))}
          </View>
        </>
      )}

      {/* Quality KPIs */}
      {stats && (
        <>
          <SectionHdr title="ANTWORT-QUALITÄT" />
          <View style={s.card}>
            <View style={s.qualRow}>
              <View style={s.qualTile}>
                <Text style={s.qualValue}>
                  {stats.total_answers_submitted > 0
                    ? Math.round((stats.valid_answers / stats.total_answers_submitted) * 100)
                    : 0}%
                </Text>
                <Text style={s.qualLabel}>Akzeptiert</Text>
              </View>
              <View style={s.qualTile}>
                <Text style={s.qualValue}>{stats.corrections_count}</Text>
                <Text style={s.qualLabel}>Korrekturen</Text>
              </View>
              <View style={s.qualTile}>
                <Text style={s.qualValue}>{stats.answers_last_7_days}</Text>
                <Text style={s.qualLabel}>7-Tage</Text>
              </View>
              <View style={s.qualTile}>
                <Text style={s.qualValue}>{stats.total_answers_submitted}</Text>
                <Text style={s.qualLabel}>Gesamt</Text>
              </View>
            </View>
          </View>
        </>
      )}

      {/* Answer history */}
      {answers.length > 0 && (
        <>
          <SectionHdr title="LETZTE ANTWORTEN" />
          {answers.map((a) => (
            <AnswerCard key={a.id} a={a} />
          ))}
        </>
      )}

      {answers.length === 0 && !loading && (
        <View style={s.emptyBox}>
          <Feather name="book-open" size={28} color={C.dim} />
          <Text style={s.emptyText}>
            Noch keine Antworten.{"\n"}Starte den Lern-Modus, um Antworten zu sehen.
          </Text>
        </View>
      )}

      <View style={{ height: insets.bottom + S.xl }} />
    </ScrollView>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────

const s = StyleSheet.create({
  root:          { flex: 1, backgroundColor: C.background },
  content:       { paddingHorizontal: S.md, paddingTop: S.sm },
  center:        { flex: 1, alignItems: "center", justifyContent: "center", gap: S.sm },
  loadingText:   { color: C.mid, fontSize: F.sm },

  header:        { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: S.md },
  title:         { fontSize: F.xl, fontWeight: W.heavy, color: C.text, letterSpacing: -0.5 },
  refreshBtn:    { padding: S.xs },

  errorBox:      { flexDirection: "row", gap: S.xs, backgroundColor: "#FEF2F2", borderRadius: R.sm, padding: S.sm, marginBottom: S.sm },
  errorText:     { color: "#DC2626", fontSize: F.sm, flex: 1 },

  // KPI tiles
  kpiRow:        { flexDirection: "row", gap: S.sm, marginBottom: S.md },
  kpiTile:       { flex: 1, backgroundColor: C.card, borderRadius: R.md, padding: S.sm, alignItems: "center", borderWidth: 1, borderColor: C.border },
  kpiValue:      { fontSize: F.md, fontWeight: W.heavy, color: C.primary, letterSpacing: -0.3 },
  kpiLabel:      { fontSize: 9, color: C.mid, marginTop: 2, textAlign: "center", textTransform: "uppercase", letterSpacing: 0.5 },
  kpiSub:        { fontSize: 8, color: C.dim, marginTop: 1 },

  // Progress card
  progressCard:  { backgroundColor: C.card, borderRadius: R.md, padding: S.md, marginBottom: S.md, borderWidth: 1, borderColor: C.border },
  progressLabelRow: { flexDirection: "row", justifyContent: "space-between", marginBottom: S.xs },
  progressLabel: { fontSize: F.sm, fontWeight: W.semi, color: C.text },
  progressPct:   { fontSize: F.sm, fontWeight: W.heavy, color: C.primary },
  progressTrack: { height: 8, backgroundColor: C.surface, borderRadius: 4, overflow: "hidden", marginBottom: S.xs },
  progressFill:  { height: "100%", backgroundColor: C.primary, borderRadius: 4 },
  progressSub:   { fontSize: F.xs, color: C.mid },

  // Section header
  sectionHdr:     { flexDirection: "row", alignItems: "center", gap: S.sm, marginBottom: S.sm, marginTop: S.md },
  sectionHdrText: { fontSize: F.xs, fontWeight: W.heavy, color: C.mid, letterSpacing: 1.2, textTransform: "uppercase" },
  sectionLine:    { flex: 1, height: 1, backgroundColor: C.border },

  card:          { backgroundColor: C.card, borderRadius: R.md, borderWidth: 1, borderColor: C.border, overflow: "hidden", marginBottom: S.sm },
  searchWrap:    { flexDirection: "row", alignItems: "center", gap: S.xs, paddingHorizontal: S.md, paddingVertical: S.sm, borderBottomWidth: 1, borderBottomColor: C.border },
  searchInput:   { flex: 1, color: C.text, fontSize: F.sm, paddingVertical: 0 },
  fileRow:       { flexDirection: "row", alignItems: "center", gap: S.sm, paddingHorizontal: S.md, paddingVertical: S.sm, borderBottomWidth: 1, borderBottomColor: C.border },
  fileName:      { fontSize: F.sm, fontWeight: W.semi, color: C.text },
  fileMeta:      { fontSize: F.xs, color: C.mid, marginTop: 2 },
  fileEmpty:     { padding: S.md, color: C.mid, fontSize: F.sm },

  // Corpus rows
  corpusRow:      { borderBottomWidth: 1, borderBottomColor: C.border },
  corpusHeader:   { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: S.md, paddingVertical: S.sm },
  corpusHeaderLeft: { flexDirection: "row", alignItems: "center", gap: S.xs, flex: 1 },
  corpusName:     { fontSize: F.sm, fontWeight: W.semi, color: C.text },
  corpusBadge:    { borderRadius: R.xs, paddingHorizontal: S.xs, paddingVertical: 2 },
  corpusBadgeText: { fontSize: F.xs, color: C.mid },
  corpusArtCount: { fontSize: F.xs, color: C.mid },
  corpusDetails:  { paddingHorizontal: S.md, paddingBottom: S.sm, gap: 3 },
  corpusDetailLine: { fontSize: F.xs, color: C.mid, lineHeight: 18 },
  link:           { color: C.primary, textDecorationLine: "underline" },

  // Category groups
  catGroup:      { borderBottomWidth: 1, borderBottomColor: C.border, paddingBottom: S.xs },
  catHeader:     { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: S.md, paddingVertical: S.sm },
  catHeaderLeft: { flexDirection: "row", alignItems: "center", gap: S.xs },
  catName:       { fontSize: F.sm, fontWeight: W.semi, color: C.text },
  catAvg:        { fontSize: F.sm, fontWeight: W.heavy, color: C.primary },

  topicRow:      { flexDirection: "row", alignItems: "center", gap: S.xs, paddingHorizontal: S.md, paddingVertical: S.xs },
  topicDot:      { width: 7, height: 7, borderRadius: 4 },
  topicName:     { fontSize: F.xs, color: C.text, width: 110 },
  topicBarWrap:  { flex: 1, height: 5, backgroundColor: C.surface, borderRadius: 3, overflow: "hidden" },
  topicBarFill:  { height: "100%", borderRadius: 3 },
  topicPct:      { fontSize: F.xs, fontWeight: W.semi, width: 30, textAlign: "right" },
  topicQ:        { fontSize: 9, color: C.dim, width: 24, textAlign: "right" },

  // Quality
  qualRow:       { flexDirection: "row", padding: S.md, gap: S.sm },
  qualTile:      { flex: 1, alignItems: "center" },
  qualValue:     { fontSize: F.lg, fontWeight: W.heavy, color: C.text },
  qualLabel:     { fontSize: 9, color: C.mid, textAlign: "center", textTransform: "uppercase", letterSpacing: 0.4 },

  // Answer cards
  ansCard:       { backgroundColor: C.card, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.md, marginBottom: S.sm },
  ansHeader:     { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: S.xs },
  ansTopicName:  { fontSize: F.sm, fontWeight: W.semi, color: C.text, flex: 1 },
  ansRight:      { flexDirection: "row", alignItems: "center", gap: S.xs },
  ansTs:         { fontSize: F.xs, color: C.mid },
  ansDelta:      { fontSize: F.xs, fontWeight: W.semi },
  ansQ:          { fontSize: F.xs, color: C.mid, lineHeight: 18 },
  ansDivider:    { height: 1, backgroundColor: C.border, marginVertical: S.sm },
  ansLabel:      { fontSize: 9, fontWeight: W.heavy, color: C.mid, textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 2 },
  ansText:       { fontSize: F.xs, color: C.text, lineHeight: 18 },
  corpusHint:    { color: C.mid, backgroundColor: C.surface, borderRadius: R.xs, padding: S.xs, marginTop: S.xs },

  emptyBox:      { alignItems: "center", paddingVertical: S.xl, gap: S.sm },
  emptyText:     { textAlign: "center", color: C.mid, fontSize: F.sm, lineHeight: 22 },
});
