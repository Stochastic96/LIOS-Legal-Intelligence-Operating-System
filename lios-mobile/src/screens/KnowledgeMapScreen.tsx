import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  LayoutAnimation,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  UIManager,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { api, KnowledgeMap, KnowledgeMapTopic } from "../api/client";

// Enable LayoutAnimation on Android
if (Platform.OS === "android" && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

const STATUS_ICON: Record<string, string> = {
  mastered: "🏆",
  functional: "✅",
  connected: "🧩",
  learning: "📖",
  seed: "🌱",
  unknown: "🔲",
};

const STATUS_COLOR: Record<string, string> = {
  mastered: "#22c55e",
  functional: "#6366f1",
  connected: "#3b82f6",
  learning: "#f59e0b",
  seed: "#64748b",
  unknown: "#334155",
};

const STATUS_LABEL: Record<string, string> = {
  mastered: "Mastered",
  functional: "Functional",
  connected: "Connected",
  learning: "Learning",
  seed: "Seed",
  unknown: "Not started",
};

function pctColor(pct: number): string {
  if (pct >= 80) return "#22c55e"; // green
  if (pct >= 40) return "#f59e0b"; // amber
  return "#ef4444";                 // red
}

function TopicRow({
  topic,
  expanded,
  onToggle,
}: {
  topic: KnowledgeMapTopic;
  expanded: boolean;
  onToggle: () => void;
}) {
  const statusColor = STATUS_COLOR[topic.status] ?? "#334155";
  const barColor = pctColor(topic.pct);
  const lastUpdated = topic.last_updated
    ? new Date(topic.last_updated).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
    : null;

  return (
    <Pressable onPress={onToggle}>
      <View style={styles.topicRow}>
        <Text style={styles.topicIcon}>{STATUS_ICON[topic.status] ?? "🔲"}</Text>
        <View style={styles.topicInfo}>
          <Text style={styles.topicName}>{topic.name}</Text>
          <View style={styles.progressBarSmall}>
            <View style={[styles.progressFillSmall, { width: `${topic.pct}%` as any, backgroundColor: barColor }]} />
          </View>
        </View>
        <View style={styles.topicRight}>
          <Text style={[styles.topicPct, { color: barColor }]}>{topic.pct}%</Text>
          <Text style={[styles.topicStatus, { color: statusColor }]}>{STATUS_LABEL[topic.status] ?? topic.status}</Text>
        </View>
        <Text style={styles.chevron}>{expanded ? "▲" : "▼"}</Text>
      </View>
      {expanded && (
        <View style={styles.topicDetail}>
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Progress</Text>
            <Text style={styles.detailValue}>{topic.pct}%</Text>
          </View>
          <View style={styles.detailRow}>
            <Text style={styles.detailLabel}>Status</Text>
            <Text style={[styles.detailValue, { color: statusColor }]}>
              {STATUS_ICON[topic.status]} {STATUS_LABEL[topic.status] ?? topic.status}
            </Text>
          </View>
          {lastUpdated && (
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Last updated</Text>
              <Text style={styles.detailValue}>{lastUpdated}</Text>
            </View>
          )}
          <View style={styles.pctBar}>
            <View style={[styles.pctBarFill, { width: `${topic.pct}%` as any, backgroundColor: barColor }]} />
          </View>
        </View>
      )}
    </Pressable>
  );
}

function CategorySection({
  name,
  topics,
  expandedIds,
  onToggle,
}: {
  name: string;
  topics: KnowledgeMapTopic[];
  expandedIds: Set<string>;
  onToggle: (id: string) => void;
}) {
  const avg = topics.length ? Math.round(topics.reduce((s, t) => s + t.pct, 0) / topics.length) : 0;
  return (
    <View style={styles.category}>
      <View style={styles.categoryHeader}>
        <Text style={styles.categoryName}>{name}</Text>
        <Text style={[styles.categoryPct, { color: pctColor(avg) }]}>{avg}%</Text>
      </View>
      {topics.map((t) => (
        <TopicRow
          key={t.id}
          topic={t}
          expanded={expandedIds.has(t.id)}
          onToggle={() => onToggle(t.id)}
        />
      ))}
    </View>
  );
}

export default function KnowledgeMapScreen() {
  const [mapData, setMapData] = useState<KnowledgeMap | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const toggleTopic = useCallback((id: string) => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  const load = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true); else setLoading(true);
    try {
      const data = await api.learn.map();
      setMapData(data);
    } catch {
      setMapData(null);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={["top"]}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#6366f1" />
        </View>
      </SafeAreaView>
    );
  }

  if (!mapData) {
    return (
      <SafeAreaView style={styles.container} edges={["top"]}>
        <View style={styles.center}>
          <Text style={styles.errorText}>Could not load knowledge map.</Text>
          <Pressable style={styles.retryBtn} onPress={() => load()}>
            <Text style={styles.retryBtnText}>Retry</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Knowledge Map</Text>
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => load(true)} tintColor="#6366f1" />}
      >
        {/* Overall progress */}
        <View style={styles.overallCard}>
          <View style={styles.overallLeft}>
            <Text style={styles.overallPct}>{mapData.overall_pct}%</Text>
            <Text style={styles.overallLabel}>field mapped</Text>
          </View>
          <View style={styles.overallStats}>
            <View style={styles.stat}>
              <Text style={[styles.statNum, { color: "#22c55e" }]}>{mapData.mastered + mapData.functional}</Text>
              <Text style={styles.statLabel}>Known</Text>
            </View>
            <View style={styles.stat}>
              <Text style={[styles.statNum, { color: "#f59e0b" }]}>{mapData.learning}</Text>
              <Text style={styles.statLabel}>Learning</Text>
            </View>
            <View style={styles.stat}>
              <Text style={[styles.statNum, { color: "#475569" }]}>{mapData.unknown}</Text>
              <Text style={styles.statLabel}>Unknown</Text>
            </View>
          </View>
        </View>

        {/* Big progress bar */}
        <View style={styles.bigProgressBar}>
          <View style={[styles.bigProgressFill, { width: `${mapData.overall_pct}%` as any }]} />
        </View>

        {/* Category sections */}
        {Object.entries(mapData.categories).map(([cat, topics]) => (
          <CategorySection
            key={cat}
            name={cat}
            topics={topics}
            expandedIds={expandedIds}
            onToggle={toggleTopic}
          />
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 32 },
  errorText: { color: "#ef4444", marginBottom: 16 },
  retryBtn: { backgroundColor: "#1e293b", borderRadius: 12, paddingHorizontal: 20, paddingVertical: 10 },
  retryBtnText: { color: "#e2e8f0", fontWeight: "600" },
  header: { paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "#1e293b" },
  headerTitle: { fontSize: 20, fontWeight: "700", color: "#e2e8f0" },
  scroll: { padding: 16 },
  overallCard: { backgroundColor: "#1e293b", borderRadius: 16, padding: 20, flexDirection: "row", alignItems: "center", marginBottom: 12 },
  overallLeft: { marginRight: 20 },
  overallPct: { fontSize: 44, fontWeight: "800", color: "#6366f1" },
  overallLabel: { fontSize: 13, color: "#64748b", marginTop: -4 },
  overallStats: { flex: 1, flexDirection: "row", justifyContent: "space-around" },
  stat: { alignItems: "center" },
  statNum: { fontSize: 22, fontWeight: "700" },
  statLabel: { fontSize: 11, color: "#64748b", marginTop: 2 },
  bigProgressBar: { height: 8, backgroundColor: "#1e293b", borderRadius: 4, marginBottom: 24, overflow: "hidden" },
  bigProgressFill: { height: "100%", backgroundColor: "#6366f1", borderRadius: 4 },
  category: { marginBottom: 20 },
  categoryHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 10 },
  categoryName: { fontSize: 13, fontWeight: "700", color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.8 },
  categoryPct: { fontSize: 12, color: "#64748b" },
  topicRow: { flexDirection: "row", alignItems: "center", backgroundColor: "#1e293b", borderRadius: 12, padding: 12, marginBottom: 2, gap: 10 },
  topicIcon: { fontSize: 20, width: 28, textAlign: "center" },
  topicInfo: { flex: 1 },
  topicName: { fontSize: 14, fontWeight: "600", color: "#e2e8f0", marginBottom: 4 },
  progressBarSmall: { height: 4, backgroundColor: "#0f172a", borderRadius: 2, overflow: "hidden" },
  progressFillSmall: { height: "100%", borderRadius: 2 },
  topicRight: { alignItems: "flex-end", marginRight: 4 },
  topicPct: { fontSize: 13, fontWeight: "700" },
  topicStatus: { fontSize: 10, fontWeight: "600", marginTop: 2 },
  chevron: { fontSize: 10, color: "#475569", width: 12, textAlign: "center" },
  topicDetail: {
    backgroundColor: "#0f172a",
    borderRadius: 10,
    marginBottom: 6,
    padding: 12,
    gap: 6,
  },
  detailRow: { flexDirection: "row", justifyContent: "space-between" },
  detailLabel: { fontSize: 12, color: "#64748b" },
  detailValue: { fontSize: 12, color: "#cbd5e1", fontWeight: "600" },
  pctBar: { height: 6, backgroundColor: "#1e293b", borderRadius: 3, marginTop: 6, overflow: "hidden" },
  pctBarFill: { height: "100%", borderRadius: 3 },
});
