import React from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Linking,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useQuery } from "@tanstack/react-query";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { getJob } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import type { RootStackParamList } from "../navigation/types";

type Props = NativeStackScreenProps<RootStackParamList, "JobDetail">;

export default function JobDetailScreen({ route, navigation }: Props) {
  const { jobId } = route.params;

  const { data: job, isLoading, error } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    refetchInterval: (data) =>
      data?.status === "PROCESSING" || data?.status === "PENDING" ? 5_000 : false,
  });

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2563EB" />
      </View>
    );
  }

  if (error || !job) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>작업 데이터를 불러올 수 없습니다.</Text>
      </View>
    );
  }

  const script = job.script;
  const variantB = job.script_variant_b;

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        {/* 헤더 */}
        <View style={styles.headerRow}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
            <Text style={styles.backText}>← 뒤로</Text>
          </TouchableOpacity>
          <StatusBadge status={job.status} />
        </View>

        {/* 기본 정보 */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>📋 작업 정보</Text>
          <InfoRow label="ID" value={job.id.slice(0, 8) + "..."} />
          <InfoRow label="플랫폼" value={job.platform.toUpperCase()} />
          <InfoRow
            label="생성일"
            value={new Date(job.created_at).toLocaleString("ko-KR")}
          />
          {job.ab_test && <InfoRow label="A/B 테스트" value="활성화" />}
        </View>

        {/* 원본 URL */}
        <TouchableOpacity
          style={styles.linkCard}
          onPress={() => Linking.openURL(job.instagram_url)}
          activeOpacity={0.7}
        >
          <Text style={styles.linkText} numberOfLines={1}>
            📎 원본: {job.instagram_url}
          </Text>
        </TouchableOpacity>

        {/* 게시 URL (완료 시) */}
        {job.post_url && (
          <TouchableOpacity
            style={[styles.linkCard, styles.postLinkCard]}
            onPress={() => Linking.openURL(job.post_url!)}
            activeOpacity={0.7}
          >
            <Text style={[styles.linkText, styles.postLinkText]} numberOfLines={1}>
              🔗 게시된 URL: {job.post_url}
            </Text>
          </TouchableOpacity>
        )}

        {/* 오류 메시지 */}
        {job.error_message && (
          <View style={styles.errorCard}>
            <Text style={styles.errorCardTitle}>⚠️ 오류 내용</Text>
            <Text style={styles.errorCardText}>{job.error_message}</Text>
          </View>
        )}

        {/* 스크립트 A */}
        {script && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>📝 스크립트 A</Text>
            <ScriptBlock script={script} />
          </View>
        )}

        {/* 스크립트 B (A/B 테스트) */}
        {variantB && (
          <View style={[styles.card, styles.variantBCard]}>
            <Text style={styles.cardTitle}>📝 스크립트 B (A/B 테스트)</Text>
            <ScriptBlock script={variantB} />
          </View>
        )}

        {/* 분석 버튼 */}
        {job.status === "COMPLETED" && (
          <TouchableOpacity
            style={styles.analyticsBtn}
            onPress={() => navigation.navigate("Analytics", { jobId })}
            activeOpacity={0.8}
          >
            <Text style={styles.analyticsBtnText}>📊 성과 분석 보기</Text>
          </TouchableOpacity>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

function ScriptBlock({ script }: { script: any }) {
  return (
    <View style={styles.scriptBlock}>
      {script.cover_text && (
        <View style={styles.scriptPart}>
          <Text style={styles.partLabel}>커버 문구</Text>
          <Text style={styles.coverText}>{script.cover_text}</Text>
        </View>
      )}
      {[
        { key: "hook", label: "훅" },
        { key: "body", label: "본문" },
        { key: "cta", label: "CTA" },
      ].map(({ key, label }) =>
        script[key] ? (
          <View key={key} style={styles.scriptPart}>
            <Text style={styles.partLabel}>{label}</Text>
            <Text style={styles.partText}>{script[key]}</Text>
          </View>
        ) : null
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#F9FAFB" },
  container: { padding: 16, paddingBottom: 40 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  errorText: { fontSize: 14, color: "#DC2626" },

  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  },
  backBtn: { padding: 4 },
  backText: { fontSize: 14, color: "#2563EB", fontWeight: "600" },

  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 14,
    padding: 14,
    marginBottom: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  cardTitle: { fontSize: 14, fontWeight: "700", color: "#111827", marginBottom: 10 },
  variantBCard: { borderWidth: 1, borderColor: "#C7D2FE" },

  infoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 5,
    borderBottomWidth: 1,
    borderColor: "#F3F4F6",
  },
  infoLabel: { fontSize: 13, color: "#6B7280" },
  infoValue: { fontSize: 13, color: "#111827", fontWeight: "500" },

  linkCard: {
    backgroundColor: "#EFF6FF",
    borderRadius: 10,
    padding: 12,
    marginBottom: 10,
  },
  postLinkCard: { backgroundColor: "#D1FAE5" },
  linkText: { fontSize: 12, color: "#1D4ED8" },
  postLinkText: { color: "#065F46" },

  errorCard: {
    backgroundColor: "#FEF2F2",
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
  },
  errorCardTitle: { fontSize: 13, fontWeight: "600", color: "#DC2626", marginBottom: 4 },
  errorCardText: { fontSize: 12, color: "#B91C1C", lineHeight: 18 },

  scriptBlock: { gap: 10 },
  scriptPart: {},
  partLabel: { fontSize: 11, fontWeight: "700", color: "#6B7280", marginBottom: 3, textTransform: "uppercase" },
  coverText: { fontSize: 18, fontWeight: "700", color: "#111827" },
  partText: { fontSize: 13, color: "#374151", lineHeight: 20 },

  analyticsBtn: {
    backgroundColor: "#F0FDF4",
    borderWidth: 1,
    borderColor: "#6EE7B7",
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
    marginTop: 4,
  },
  analyticsBtnText: { fontSize: 14, fontWeight: "600", color: "#065F46" },
});
