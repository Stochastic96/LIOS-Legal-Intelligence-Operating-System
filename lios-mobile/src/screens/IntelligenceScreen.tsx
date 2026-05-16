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

// ── Status colour helpers ───────────────────────────────────────────────────────

const STATUS_COLOR: Record<string, string> = {
  mastered:   "#10B981",
  functional: "#3B82F6",
  connected:  "#8B5CF6",
  learning:   "#F59E0B",
  seed:       "#6B7280",
  unknown:    "#9CA3AF",
};

function statusColor(status: string): string {
  return STATUS_COLOR[status] ?? C.dim;
}

// ── Knowledge Summary Card ─────────────────────────────────────────────────────

function KnowledgeSummaryCard({
  stats,
  mastered,
  functional,
  learning,
  unknown,
}: {
  stats: IntelligenceStats;
  mastered: number;
  functional: number;
  learning: number;
  unknown: number;
}) {
  const pct = Math.min(100, stats.overall_learning_pct);
  const barColor =
    pct >= 70 ? "#10B981" : pct >= 40 ? "#3B82F6" : "#F59E0B";

  const pills = [
    { label: "Mastered",   count: mastered,   color: "#10B981", bg: "#D1FAE5" },
    { label: "Functional", count: functional, color: "#3B82F6", bg: "#DBEAFE" },
    { label: "Learning",   count: learning,   color: "#F59E0B", bg: "#FEF3C7" },
    { label: "Unknown",    count: unknown,    color: "#9CA3AF", bg: C.surface },
  ];

  return (
    <View style={s.heroCard}>
      <View style={s.heroTop}>
        <View>
          <Text style={s.heroLabel}>KNOWLEDGE STATUS</Text>
          <Text style={s.heroTitle}>LIOS Brain</Text>
        </View>
        <View style={[s.heroPctBox, { borderColor: barColor + "44" }]}>
          <Text style={[s.heroPct, { color: barColor }]}>{pct}%</Text>
          <Text style={s.heroPctSub}>mastered</Text>
        </View>
      </View>

      <View style={s.heroBarTrack}>
        <View style={[s.heroBarFill, { width: `${pct}%` as any, backgroundColor: barColor }]} />
      </View>

      <View style={s.pillRow}>
        {pills.map((p) => (
          <View key={p.label} style={[s.pill, { backgroundColor: p.bg }]}>
            <View style={[s.pillDot, { backgroundColor: p.color }]} />
            <Text style={[s.pillCount, { color: p.color }]}>{p.count}</Text>
            <Text style={[s.pillLabel, { color: p.color }]}>{p.label}</Text>
          </View>
        ))}
      </View>

      <Text style={s.heroFooter}>
        {stats.total_chunks.toLocaleString()} chunks · {stats.total_regulations} regulations · {stats.consumed_files} documents
      </Text>
    </View>
  );
}

// ── Autolearn Activity Card ────────────────────────────────────────────────────

function ActivityCard({ stats }: { stats: IntelligenceStats }) {
  const acceptRate =
    stats.total_answers_submitted > 0
      ? Math.round((stats.valid_answers / stats.total_answers_submitted) * 100)
      : 0;

  const tiles = [
    { value: stats.total_answers_submitted, label: "Answered" },
    { value: `${acceptRate}%`,              label: "Accepted" },
    { value: stats.answers_last_7_days,     label: "This Week" },
    { value: stats.corrections_count,       label: "Corrections" },
  ];

  return (
    <View style={s.actCard}>
      <View style={s.actHeader}>
        <Feather name="zap" size={14} color={C.primary} />
        <Text style={s.actTitle}>AUTOLEARN ACTIVITY</Text>
        <Text style={s.actSub}>{stats.total_questions_in_bank} questions in bank</Text>
      </View>
      <View style={s.actTiles}>
        {tiles.map((t) => (
          <View key={t.label} style={s.actTile}>
            <Text style={s.actValue}>{t.value}</Text>
            <Text style={s.actLabel}>{t.label}</Text>
          </View>
        ))}
      </View>
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
    Animated.timing(anim, { toValue: open ? 0 : 1, duration: 220, useNativeDriver: false }).start();
    setOpen(!open);
  }

  return (
    <View style={s.corpusRow}>
      <Pressable style={s.corpusHeader} onPress={toggle}>
        <View style={s.corpusHeaderLeft}>
          <Feather name={open ? "chevron-down" : "chevron-right"} size={14} color={C.mid} />
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
            <Text style={s.corpusDetailLine}>Published: {reg.published_date}</Text>
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
              Articles: {reg.articles.slice(0, 10).join(", ")}
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
            <View style={[s.topicDot, { backgroundColor: statusColor(t.status) }]} />
            <Text style={s.topicName} numberOfLines={1}>{t.name}</Text>
            <View style={s.topicBarWrap}>
              <View style={[s.topicBarFill, { width: `${t.pct}%` as any, backgroundColor: statusColor(t.status) }]} />
            </View>
            <Text style={[s.topicPct, { color: statusColor(t.status) }]}>{t.pct}%</Text>
            {t.questions_in_bank > 0 && (
              <Text style={s.topicQ}>{t.questions_in_bank}Q</Text>
            )}
          </View>
        ))}
    </View>
  );
}

// ��─ Answer card ────────────────────────────────────────────────────────────────

function AnswerCard({ a }: { a: AnswerRecord }) {
  const [open, setOpen] = useState(false);
  const ts = a.ts ? new Date(a.ts).toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit" }) : "";
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
          <Text style={s.ansLabel}>Your answer</Text>
          <Text style={s.ansText}>{a.user_answer || "—"}</Text>
          {a.corpus_hint ? (
            <>
              <Text style={s.ansLabel}>Corpus reference</Text>
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
          {file.regulation} · {file.chunk_count} chunks · {file.article_count} articles
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

  const [loading, setLoading]    = useState(true);
  const [refreshing, setRefresh] = useState(false);
  const [stats, setStats]        = useState<IntelligenceStats | null>(null);
  const [corpus, setCorpus]      = useState<CorpusRegulation[]>([]);
  const [topics, setTopics]      = useState<TopicCoverage[]>([]);
  const [answers, setAnswers]    = useState<AnswerRecord[]>([]);
  const [files, setFiles]        = useState<CorpusFileRecord[]>([]);
  const [fileQuery, setFileQuery] = useState("");
  const [error, setError]        = useState<string | null>(null);

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
      setError(e?.message ?? "Connection error");
    } finally {
      setLoading(false);
      setRefresh(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const handle = setTimeout(() => {
      api.intelligence.files(fileQuery, 30)
        .then((r) => setFiles(r.files))
        .catch(() => setFiles([]));
    }, 180);
    return () => clearTimeout(handle);
  }, [fileQuery]);

  // Status counts derived from topics (no extra API call needed)
  const mastered   = topics.filter(t => t.status === "mastered").length;
  const functional = topics.filter(t => t.status === "functional").length;
  const learning   = topics.filter(t => ["learning", "connected"].includes(t.status)).length;
  const unknown    = topics.filter(t => ["unknown", "seed"].includes(t.status)).length;

  const byCategory = topics.reduce<Record<string, TopicCoverage[]>>((acc, t) => {
    const c = t.category || "Other";
    (acc[c] = acc[c] || []).push(t);
    return acc;
  }, {});

  if (loading) {
    return (
      <View style={[s.center, { paddingTop: insets.top }]}>
        <ActivityIndicator size="large" color={C.primary} />
        <Text style={s.loadingText}>Loading intelligence data…</Text>
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
        <Text style={s.title}>Intelligence</Text>
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

      {/* Hero — knowledge summary */}
      {stats && (
        <KnowledgeSummaryCard
          stats={stats}
          mastered={mastered}
          functional={functional}
          learning={learning}
          unknown={unknown}
        />
      )}

      {/* Autolearn activity */}
      {stats && <ActivityCard stats={stats} />}

      {/* Topic coverage */}
      {Object.keys(byCategory).length > 0 && (
        <>
          <SectionHdr title="TOPIC COVERAGE" />
          <View style={s.card}>
            {Object.entries(byCategory).map(([cat, ts]) => (
              <CategoryGroup key={cat} cat={cat} topics={ts} />
            ))}
          </View>
        </>
      )}

      {/* Knowledge base (regulations) */}
      {corpus.length > 0 && (
        <>
          <SectionHdr title="KNOWLEDGE BASE" />
          <View style={s.card}>
            {corpus.map((reg) => (
              <CorpusRow
                key={`${reg.regulation}-${reg.celex_id || reg.source_url || reg.last_indexed || reg.article_count}`}
                reg={reg}
              />
            ))}
          </View>
        </>
      )}

      {/* Ingested documents */}
      <SectionHdr title="INGESTED DOCUMENTS" />
      <View style={s.card}>
        <View style={s.searchWrap}>
          <Feather name="search" size={15} color={C.dim} />
          <TextInput
            style={s.searchInput}
            value={fileQuery}
            onChangeText={setFileQuery}
            placeholder="Search by filename, e.g. CSRD or Francovich"
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
            {fileQuery.trim() ? "No files matching the search." : "No corpus files visible yet."}
          </Text>
        )}
      </View>

      {/* Recent answers */}
      {answers.length > 0 && (
        <>
          <SectionHdr title="RECENT ANSWERS" />
          {answers.map((a) => (
            <AnswerCard key={a.id} a={a} />
          ))}
        </>
      )}

      {answers.length === 0 && !loading && (
        <View style={s.emptyBox}>
          <Feather name="book-open" size={28} color={C.dim} />
          <Text style={s.emptyText}>
            No answers yet.{"\n"}Start Learn Mode to see your Q&A history.
          </Text>
        </View>
      )}

      <View style={{ height: insets.bottom + S.xl }} />
    </ScrollView>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────

const s = StyleSheet.create({
  root:        { flex: 1, backgroundColor: C.background },
  content:     { paddingHorizontal: S.md, paddingTop: S.sm },
  center:      { flex: 1, alignItems: "center", justifyContent: "center", gap: S.sm },
  loadingText: { color: C.mid, fontSize: F.sm },

  header:     { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: S.md },
  title:      { fontSize: F.xl, fontWeight: W.heavy, color: C.text, letterSpacing: -0.5 },
  refreshBtn: { padding: S.xs },

  errorBox:  { flexDirection: "row", gap: S.xs, backgroundColor: "#FEF2F2", borderRadius: R.sm, padding: S.sm, marginBottom: S.sm },
  errorText: { color: "#DC2626", fontSize: F.sm, flex: 1 },

  // Hero card
  heroCard:     { backgroundColor: C.card, borderRadius: R.md, padding: S.md, marginBottom: S.sm, borderWidth: 1, borderColor: C.border },
  heroTop:      { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: S.sm },
  heroLabel:    { fontSize: 10, fontWeight: W.heavy, color: C.mid, letterSpacing: 1.2, textTransform: "uppercase" },
  heroTitle:    { fontSize: F.lg, fontWeight: W.heavy, color: C.text, marginTop: 2 },
  heroPctBox:   { alignItems: "center", borderWidth: 1, borderRadius: R.sm, paddingHorizontal: S.sm, paddingVertical: 4 },
  heroPct:      { fontSize: F.xxl, fontWeight: W.heavy, lineHeight: F.xxl * 1.1 },
  heroPctSub:   { fontSize: 9, color: C.mid, textTransform: "uppercase", letterSpacing: 0.5 },
  heroBarTrack: { height: 12, backgroundColor: C.surface, borderRadius: 6, overflow: "hidden", marginBottom: S.sm },
  heroBarFill:  { height: "100%", borderRadius: 6 },
  pillRow:      { flexDirection: "row", gap: S.xs, marginBottom: S.sm },
  pill:         { flex: 1, flexDirection: "row", alignItems: "center", gap: 4, borderRadius: R.xs, paddingHorizontal: 6, paddingVertical: 5 },
  pillDot:      { width: 6, height: 6, borderRadius: 3 },
  pillCount:    { fontSize: F.sm, fontWeight: W.heavy },
  pillLabel:    { fontSize: 9, fontWeight: W.semi },
  heroFooter:   { fontSize: F.xs, color: C.mid },

  // Activity card
  actCard:    { backgroundColor: C.card, borderRadius: R.md, padding: S.md, marginBottom: S.md, borderWidth: 1, borderColor: C.border },
  actHeader:  { flexDirection: "row", alignItems: "center", gap: S.xs, marginBottom: S.sm },
  actTitle:   { fontSize: 10, fontWeight: W.heavy, color: C.mid, letterSpacing: 1.2, flex: 1 },
  actSub:     { fontSize: F.xs, color: C.dim },
  actTiles:   { flexDirection: "row", gap: S.sm },
  actTile:    { flex: 1, alignItems: "center", backgroundColor: C.surface, borderRadius: R.xs, paddingVertical: S.sm },
  actValue:   { fontSize: F.lg, fontWeight: W.heavy, color: C.text },
  actLabel:   { fontSize: 9, color: C.mid, textTransform: "uppercase", letterSpacing: 0.4, marginTop: 2 },

  // Section header
  sectionHdr:     { flexDirection: "row", alignItems: "center", gap: S.sm, marginBottom: S.sm, marginTop: S.md },
  sectionHdrText: { fontSize: F.xs, fontWeight: W.heavy, color: C.mid, letterSpacing: 1.2, textTransform: "uppercase" },
  sectionLine:    { flex: 1, height: 1, backgroundColor: C.border },

  card:       { backgroundColor: C.card, borderRadius: R.md, borderWidth: 1, borderColor: C.border, overflow: "hidden", marginBottom: S.sm },
  searchWrap: { flexDirection: "row", alignItems: "center", gap: S.xs, paddingHorizontal: S.md, paddingVertical: S.sm, borderBottomWidth: 1, borderBottomColor: C.border },
  searchInput:{ flex: 1, color: C.text, fontSize: F.sm, paddingVertical: 0 },
  fileRow:    { flexDirection: "row", alignItems: "center", gap: S.sm, paddingHorizontal: S.md, paddingVertical: S.sm, borderBottomWidth: 1, borderBottomColor: C.border },
  fileName:   { fontSize: F.sm, fontWeight: W.semi, color: C.text },
  fileMeta:   { fontSize: F.xs, color: C.mid, marginTop: 2 },
  fileEmpty:  { padding: S.md, color: C.mid, fontSize: F.sm },

  // Corpus rows
  corpusRow:        { borderBottomWidth: 1, borderBottomColor: C.border },
  corpusHeader:     { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: S.md, paddingVertical: S.sm },
  corpusHeaderLeft: { flexDirection: "row", alignItems: "center", gap: S.xs, flex: 1 },
  corpusName:       { fontSize: F.sm, fontWeight: W.semi, color: C.text },
  corpusBadge:      { borderRadius: R.xs, paddingHorizontal: S.xs, paddingVertical: 2 },
  corpusBadgeText:  { fontSize: F.xs, color: C.mid },
  corpusArtCount:   { fontSize: F.xs, color: C.mid },
  corpusDetails:    { paddingHorizontal: S.md, paddingBottom: S.sm, gap: 3 },
  corpusDetailLine: { fontSize: F.xs, color: C.mid, lineHeight: 18 },
  link:             { color: C.primary, textDecorationLine: "underline" },

  // Category groups
  catGroup:      { borderBottomWidth: 1, borderBottomColor: C.border, paddingBottom: S.xs },
  catHeader:     { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: S.md, paddingVertical: S.sm },
  catHeaderLeft: { flexDirection: "row", alignItems: "center", gap: S.xs },
  catName:       { fontSize: F.sm, fontWeight: W.semi, color: C.text },
  catAvg:        { fontSize: F.sm, fontWeight: W.heavy, color: C.primary },

  topicRow:    { flexDirection: "row", alignItems: "center", gap: S.xs, paddingHorizontal: S.md, paddingVertical: S.xs },
  topicDot:    { width: 7, height: 7, borderRadius: 4 },
  topicName:   { fontSize: F.xs, color: C.text, width: 110 },
  topicBarWrap:{ flex: 1, height: 5, backgroundColor: C.surface, borderRadius: 3, overflow: "hidden" },
  topicBarFill:{ height: "100%", borderRadius: 3 },
  topicPct:    { fontSize: F.xs, fontWeight: W.semi, width: 30, textAlign: "right" },
  topicQ:      { fontSize: 9, color: C.dim, width: 24, textAlign: "right" },

  // Answer cards
  ansCard:      { backgroundColor: C.card, borderRadius: R.md, borderWidth: 1, borderColor: C.border, padding: S.md, marginBottom: S.sm },
  ansHeader:    { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: S.xs },
  ansTopicName: { fontSize: F.sm, fontWeight: W.semi, color: C.text, flex: 1 },
  ansRight:     { flexDirection: "row", alignItems: "center", gap: S.xs },
  ansTs:        { fontSize: F.xs, color: C.mid },
  ansDelta:     { fontSize: F.xs, fontWeight: W.semi },
  ansQ:         { fontSize: F.xs, color: C.mid, lineHeight: 18 },
  ansDivider:   { height: 1, backgroundColor: C.border, marginVertical: S.sm },
  ansLabel:     { fontSize: 9, fontWeight: W.heavy, color: C.mid, textTransform: "uppercase", letterSpacing: 0.8, marginBottom: 2 },
  ansText:      { fontSize: F.xs, color: C.text, lineHeight: 18 },
  corpusHint:   { color: C.mid, backgroundColor: C.surface, borderRadius: R.xs, padding: S.xs, marginTop: S.xs },

  emptyBox:  { alignItems: "center", paddingVertical: S.xl, gap: S.sm },
  emptyText: { textAlign: "center", color: C.mid, fontSize: F.sm, lineHeight: 22 },
});
