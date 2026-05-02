import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { api, KnowledgeMap, KnowledgeMapTopic } from "../api/client";
import AnimatedProgressBar from "../components/AnimatedProgressBar";
import Card from "../components/Card";
import SectionHeader from "../components/SectionHeader";
import ScalePressable from "../components/ScalePressable";
import { C, F, R, S, W, pctColor } from "../theme";

const STATUS_ICON: Record<string, string> = {
  mastered:   "🏆",
  functional: "✅",
  connected:  "🧩",
  learning:   "📖",
  seed:       "🌱",
  unknown:    "🔲",
};

const STATUS_COLOR: Record<string, string> = {
  mastered:   C.green,
  functional: C.accent,
  connected:  C.accent,
  learning:   C.amber,
  seed:       C.mid,
  unknown:    C.dim,
};

const STATUS_LABEL: Record<string, string> = {
  mastered:   "Mastered",
  functional: "Functional",
  connected:  "Connected",
  learning:   "Learning",
  seed:       "Seed",
  unknown:    "Not started",
};

const DETAIL_HEIGHT = 148;

function TopicRow({
  topic,
  expanded,
  onToggle,
}: {
  topic: KnowledgeMapTopic;
  expanded: boolean;
  onToggle: () => void;
}) {
  const expandAnim = useRef(new Animated.Value(expanded ? 1 : 0)).current;
  const statusColor = STATUS_COLOR[topic.status] ?? C.dim;
  const barColor = pctColor(topic.pct);
  const lastUpdated = topic.last_updated
    ? new Date(topic.last_updated).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : null;

  useEffect(() => {
    Animated.spring(expandAnim, {
      toValue: expanded ? 1 : 0,
      speed: 18,
      bounciness: 3,
      useNativeDriver: false,
    }).start();
  }, [expanded]);

  const detailHeight = expandAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0, DETAIL_HEIGHT],
  });
  const detailOpacity = expandAnim.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [0, 0, 1],
  });

  return (
    <ScalePressable onPress={onToggle} style={styles.topicPressable}>
      <Card surface="s2" style={styles.topicCard}>
        <View style={styles.topicRow}>
          <Text style={styles.topicIcon}>{STATUS_ICON[topic.status] ?? "🔲"}</Text>
          <View style={styles.topicInfo}>
            <Text style={styles.topicName}>{topic.name}</Text>
            <AnimatedProgressBar
              value={topic.pct}
              color={barColor}
              height={4}
              bgColor={C.bg}
              duration={600}
            />
          </View>
          <View style={styles.topicRight}>
            <Text style={[styles.topicPct, { color: barColor }]}>{topic.pct}%</Text>
            <Text style={[styles.topicStatus, { color: statusColor }]}>
              {STATUS_LABEL[topic.status] ?? topic.status}
            </Text>
          </View>
          <Feather
            name={expanded ? "chevron-up" : "chevron-down"}
            size={14}
            color={C.dim}
            style={styles.chevron}
          />
        </View>

        <Animated.View style={{ height: detailHeight, overflow: "hidden" }}>
          <Animated.View style={[styles.topicDetail, { opacity: detailOpacity }]}>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Progress</Text>
              <Text style={[styles.detailValue, { color: barColor }]}>{topic.pct}%</Text>
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
            <View style={styles.detailBarWrap}>
              <AnimatedProgressBar
                value={topic.pct}
                color={barColor}
                height={6}
                bgColor={C.s1}
                duration={500}
              />
            </View>
          </Animated.View>
        </Animated.View>
      </Card>
    </ScalePressable>
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
  const avg = topics.length
    ? Math.round(topics.reduce((s, t) => s + t.pct, 0) / topics.length)
    : 0;

  return (
    <View style={styles.category}>
      <SectionHeader
        label={name}
        right={
          <Text style={[styles.categoryAvg, { color: pctColor(avg) }]}>{avg}%</Text>
        }
      />
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

  const mountAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(mountAnim, {
      toValue: 1,
      duration: 320,
      useNativeDriver: true,
    }).start();
  }, []);

  const toggleTopic = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const load = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true);
    else setLoading(true);
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

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <SafeAreaView style={styles.container} edges={["top"]}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={C.accent} />
        </View>
      </SafeAreaView>
    );
  }

  if (!mapData) {
    return (
      <SafeAreaView style={styles.container} edges={["top"]}>
        <View style={styles.center}>
          <Feather name="alert-circle" size={32} color={C.red} style={{ marginBottom: S.md }} />
          <Text style={styles.errorText}>Could not load knowledge map.</Text>
          <ScalePressable onPress={() => load()}>
            <View style={styles.retryBtn}>
              <Text style={styles.retryBtnText}>Retry</Text>
            </View>
          </ScalePressable>
        </View>
      </SafeAreaView>
    );
  }

  const fadeStyle = {
    opacity: mountAnim,
    transform: [
      {
        translateY: mountAnim.interpolate({
          inputRange: [0, 1],
          outputRange: [16, 0],
        }),
      },
    ],
  };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Knowledge Map</Text>
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => load(true)}
            tintColor={C.accent}
          />
        }
      >
        <Animated.View style={fadeStyle}>
          {/* Overall card */}
          <Card surface="s2" style={styles.overallCard}>
            <View style={styles.overallLeft}>
              <Text style={[styles.overallPct, { color: pctColor(mapData.overall_pct) }]}>
                {mapData.overall_pct}%
              </Text>
              <Text style={styles.overallLabel}>field mapped</Text>
            </View>
            <View style={styles.overallStats}>
              <View style={styles.stat}>
                <Feather name="users" size={14} color={C.green} style={{ marginBottom: 4 }} />
                <Text style={[styles.statNum, { color: C.green }]}>
                  {mapData.mastered + mapData.functional}
                </Text>
                <Text style={styles.statLabel}>Known</Text>
              </View>
              <View style={styles.statDivider} />
              <View style={styles.stat}>
                <Feather name="book-open" size={14} color={C.amber} style={{ marginBottom: 4 }} />
                <Text style={[styles.statNum, { color: C.amber }]}>{mapData.learning}</Text>
                <Text style={styles.statLabel}>Learning</Text>
              </View>
              <View style={styles.statDivider} />
              <View style={styles.stat}>
                <Feather name="help-circle" size={14} color={C.dim} style={{ marginBottom: 4 }} />
                <Text style={[styles.statNum, { color: C.mid }]}>{mapData.unknown}</Text>
                <Text style={styles.statLabel}>Unknown</Text>
              </View>
            </View>
          </Card>

          {/* Big progress bar */}
          <View style={styles.bigBarWrap}>
            <AnimatedProgressBar
              value={mapData.overall_pct}
              color={pctColor(mapData.overall_pct)}
              height={8}
              bgColor={C.s2}
              duration={700}
            />
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
        </Animated.View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: C.bg },
  center:       { flex: 1, alignItems: "center", justifyContent: "center", padding: S.xl },
  errorText:    { color: C.red, marginBottom: S.md, fontSize: F.sm },
  retryBtn:     {
    backgroundColor: C.s2,
    borderRadius: R.sm,
    borderWidth: 1,
    borderColor: C.border,
    paddingHorizontal: S.lg,
    paddingVertical: S.sm,
  },
  retryBtnText: { color: C.text, fontWeight: W.semi, fontSize: F.sm },

  header:       {
    paddingHorizontal: S.md,
    paddingVertical: S.sm + 2,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
  },
  headerTitle:  { fontSize: F.lg, fontWeight: W.bold, color: C.text },

  scroll:       { padding: S.md, paddingBottom: S.xxl },

  overallCard:  { flexDirection: "row", alignItems: "center", marginBottom: S.sm },
  overallLeft:  { marginRight: S.lg },
  overallPct:   { fontSize: 44, fontWeight: W.heavy, lineHeight: 50 },
  overallLabel: { fontSize: F.xs, color: C.dim, marginTop: -4 },
  overallStats: { flex: 1, flexDirection: "row", justifyContent: "space-around", alignItems: "center" },
  stat:         { alignItems: "center" },
  statNum:      { fontSize: F.xl, fontWeight: W.bold },
  statLabel:    { fontSize: F.xs, color: C.dim, marginTop: 2 },
  statDivider:  { width: 1, height: 36, backgroundColor: C.border },

  bigBarWrap:   { marginBottom: S.lg, marginTop: S.xs },

  category:     { marginBottom: S.lg },
  categoryAvg:  { fontSize: F.xs, fontWeight: W.semi },

  topicPressable: { marginBottom: S.xs },
  topicCard:      { padding: 0, overflow: "hidden" },
  topicRow:       { flexDirection: "row", alignItems: "center", padding: S.sm + 4, gap: S.sm },
  topicIcon:      { fontSize: 18, width: 26, textAlign: "center" },
  topicInfo:      { flex: 1, gap: 6 },
  topicName:      { fontSize: F.sm, fontWeight: W.semi, color: C.text },
  topicRight:     { alignItems: "flex-end", marginRight: S.xs },
  topicPct:       { fontSize: F.sm, fontWeight: W.bold },
  topicStatus:    { fontSize: F.xs, fontWeight: W.semi, marginTop: 2 },
  chevron:        { width: 16, textAlign: "center" },

  topicDetail:    { paddingHorizontal: S.sm + 4, paddingBottom: S.sm + 4, gap: 8 },
  detailBarWrap:  { marginTop: S.xs },
  detailRow:      { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  detailLabel:    { fontSize: F.xs, color: C.mid },
  detailValue:    { fontSize: F.xs, color: C.text, fontWeight: W.semi },
});
