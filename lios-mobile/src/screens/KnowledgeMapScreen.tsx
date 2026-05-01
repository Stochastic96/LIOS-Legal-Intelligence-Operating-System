import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { api, KnowledgeMap, KnowledgeMapTopic } from "../api/client";

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

function TopicRow({ topic }: { topic: KnowledgeMapTopic }) {
  const color = STATUS_COLOR[topic.status] ?? "#334155";
  return (
    <View style={styles.topicRow}>
      <Text style={styles.topicIcon}>{STATUS_ICON[topic.status] ?? "🔲"}</Text>
      <View style={styles.topicInfo}>
        <Text style={styles.topicName}>{topic.name}</Text>
        <View style={styles.progressBarSmall}>
          <View style={[styles.progressFillSmall, { width: `${topic.pct}%` as any, backgroundColor: color }]} />
        </View>
      </View>
      <Text style={[styles.topicStatus, { color }]}>{STATUS_LABEL[topic.status] ?? topic.status}</Text>
    </View>
  );
}

function CategorySection({ name, topics }: { name: string; topics: KnowledgeMapTopic[] }) {
  const avg = topics.length ? Math.round(topics.reduce((s, t) => s + t.pct, 0) / topics.length) : 0;
  return (
    <View style={styles.category}>
      <View style={styles.categoryHeader}>
        <Text style={styles.categoryName}>{name}</Text>
        <Text style={styles.categoryPct}>{avg}%</Text>
      </View>
      {topics.map((t) => <TopicRow key={t.id} topic={t} />)}
    </View>
  );
}

export default function KnowledgeMapScreen() {
  const [mapData, setMapData] = useState<KnowledgeMap | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

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
          <CategorySection key={cat} name={cat} topics={topics} />
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
  topicRow: { flexDirection: "row", alignItems: "center", backgroundColor: "#1e293b", borderRadius: 12, padding: 12, marginBottom: 6, gap: 10 },
  topicIcon: { fontSize: 20, width: 28, textAlign: "center" },
  topicInfo: { flex: 1 },
  topicName: { fontSize: 14, fontWeight: "600", color: "#e2e8f0", marginBottom: 4 },
  progressBarSmall: { height: 4, backgroundColor: "#0f172a", borderRadius: 2, overflow: "hidden" },
  progressFillSmall: { height: "100%", borderRadius: 2 },
  topicStatus: { fontSize: 11, fontWeight: "600", minWidth: 64, textAlign: "right" },
});
