import React from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  FlatList,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useQuery } from "@tanstack/react-query";
import { getJobAnalytics, getLeaderboard, MetricPoint, LeaderboardItem } from "../api/client";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "Analytics">;

export default function AnalyticsScreen({ route }: Props) {
  const { jobId } = route.params;

  const { data: analyticsData, isLoading: loadingAnalytics } = useQuery({
    queryKey: ["analytics", jobId],
    queryFn: () => getJobAnalytics(jobId),
  });

  const { data: leaderboard, isLoading: loadingLeaderboard } = useQuery({
    queryKey: ["leaderboard"],
    queryFn: () => getLeaderboard(10),
  });

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>📊 성과 분석</Text>

        {/* 지표 카드 */}
        <Text style={styles.sectionTitle}>⏱️ 시간대별 지표</Text>

        {loadingAnalytics ? (
          <ActivityIndicator color="#2563EB" style={styles.loader} />
        ) : !analyticsData?.metrics?.length ? (
          <View style={styles.emptyBox}>
            <Text style={styles.emptyText}>아직 성과 데이터가 없습니다.</Text>
            <Text style={styles.emptyHint}>업로드 후 24h/72h에 자동 수집됩니다.</Text>
          </View>
        ) : (
          <View style={styles.metricsGrid}>
            {(analyticsData.metrics as MetricPoint[]).map((m) => (
              <MetricCard key={m.interval_hours} metric={m} />
            ))}
          </View>
        )}

        {/* 리더보드 */}
        <Text style={[styles.sectionTitle, { marginTop: 24 }]}>🏆 72h 조회수 리더보드</Text>

        {loadingLeaderboard ? (
          <ActivityIndicator color="#2563EB" style={styles.loader} />
        ) : !leaderboard?.length ? (
          <View style={styles.emptyBox}>
            <Text style={styles.emptyText}>리더보드 데이터가 없습니다.</Text>
          </View>
        ) : (
          <View style={styles.card}>
            {(leaderboard as LeaderboardItem[]).map((item, i) => (
              <View
                key={item.job_id}
                style={[
                  styles.leaderRow,
                  i < leaderboard.length - 1 && styles.leaderRowBorder,
                  item.job_id === jobId && styles.leaderRowHighlight,
                ]}
              >
                <Text style={styles.rankText}>{i + 1}</Text>
                <View style={styles.leaderInfo}>
                  <Text style={styles.leaderCover} numberOfLines={1}>
                    {item.cover_text ?? "—"}
                  </Text>
                  <Text style={styles.leaderPlatform}>{item.platform}</Text>
                </View>
                <View style={styles.leaderMetrics}>
                  <Text style={styles.viewsText}>{item.views_72h.toLocaleString()} 조회</Text>
                  <Text style={styles.likesText}>{item.likes_72h.toLocaleString()} 좋아요</Text>
                </View>
              </View>
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function MetricCard({ metric }: { metric: MetricPoint }) {
  return (
    <View style={styles.metricCard}>
      <Text style={styles.metricInterval}>{metric.interval_hours}h 후</Text>
      <MetricRow icon="👁️" label="조회" value={metric.views} />
      <MetricRow icon="❤️" label="좋아요" value={metric.likes} />
      <MetricRow icon="💬" label="댓글" value={metric.comments} />
      <MetricRow icon="↗️" label="공유" value={metric.shares} />
      <Text style={styles.metricDate}>
        {new Date(metric.collected_at).toLocaleString("ko-KR")}
      </Text>
    </View>
  );
}

function MetricRow({ icon, label, value }: { icon: string; label: string; value: number }) {
  return (
    <View style={styles.metricRow}>
      <Text style={styles.metricIcon}>{icon}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value.toLocaleString()}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#F9FAFB" },
  container: { padding: 16, paddingBottom: 40 },
  title: { fontSize: 22, fontWeight: "700", color: "#111827", marginBottom: 20 },
  sectionTitle: { fontSize: 15, fontWeight: "700", color: "#374151", marginBottom: 12 },
  loader: { marginVertical: 20 },

  emptyBox: {
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 20,
    alignItems: "center",
  },
  emptyText: { fontSize: 14, color: "#6B7280" },
  emptyHint: { fontSize: 12, color: "#9CA3AF", marginTop: 4 },

  metricsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  metricCard: {
    flex: 1,
    minWidth: "45%",
    backgroundColor: "#FFFFFF",
    borderRadius: 14,
    padding: 14,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  metricInterval: {
    fontSize: 13,
    fontWeight: "700",
    color: "#2563EB",
    marginBottom: 10,
  },
  metricRow: { flexDirection: "row", alignItems: "center", marginBottom: 6 },
  metricIcon: { fontSize: 14, marginRight: 4 },
  metricLabel: { flex: 1, fontSize: 12, color: "#6B7280" },
  metricValue: { fontSize: 13, fontWeight: "700", color: "#111827" },
  metricDate: { fontSize: 10, color: "#9CA3AF", marginTop: 8 },

  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 14,
    overflow: "hidden",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  leaderRow: {
    flexDirection: "row",
    alignItems: "center",
    padding: 12,
    gap: 10,
  },
  leaderRowBorder: { borderBottomWidth: 1, borderColor: "#F3F4F6" },
  leaderRowHighlight: { backgroundColor: "#EFF6FF" },
  rankText: { fontSize: 16, fontWeight: "700", color: "#6B7280", width: 24, textAlign: "center" },
  leaderInfo: { flex: 1 },
  leaderCover: { fontSize: 13, fontWeight: "600", color: "#111827" },
  leaderPlatform: { fontSize: 11, color: "#6B7280", marginTop: 2 },
  leaderMetrics: { alignItems: "flex-end" },
  viewsText: { fontSize: 12, fontWeight: "700", color: "#111827" },
  likesText: { fontSize: 11, color: "#6B7280", marginTop: 2 },
});
