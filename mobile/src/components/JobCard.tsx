import React from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { Job } from "../api/client";
import StatusBadge from "./StatusBadge";

const PLATFORM_ICON: Record<string, string> = {
  instagram: "📸",
  youtube: "▶️",
  tiktok: "🎵",
};

interface Props {
  job: Job;
  onPress?: () => void;
}

export default function JobCard({ job, onPress }: Props) {
  const icon = PLATFORM_ICON[job.platform] ?? "📱";
  const date = new Date(job.created_at).toLocaleDateString("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.7} style={styles.card}>
      <View style={styles.row}>
        <Text style={styles.icon}>{icon}</Text>
        <View style={styles.info}>
          <Text style={styles.url} numberOfLines={1}>
            {job.instagram_url.replace("https://www.instagram.com/", "")}
          </Text>
          <Text style={styles.date}>{date}</Text>
        </View>
        <StatusBadge status={job.status} />
      </View>

      {job.post_url ? (
        <Text style={styles.postUrl} numberOfLines={1}>
          🔗 {job.post_url}
        </Text>
      ) : null}

      {job.error_message ? (
        <Text style={styles.error} numberOfLines={2}>
          ⚠️ {job.error_message}
        </Text>
      ) : null}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 12,
    marginBottom: 10,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  icon: {
    fontSize: 20,
  },
  info: {
    flex: 1,
    marginRight: 8,
  },
  url: {
    fontSize: 13,
    fontWeight: "600",
    color: "#111827",
  },
  date: {
    fontSize: 11,
    color: "#6B7280",
    marginTop: 2,
  },
  postUrl: {
    fontSize: 11,
    color: "#2563EB",
    marginTop: 6,
  },
  error: {
    fontSize: 11,
    color: "#DC2626",
    marginTop: 6,
  },
});
