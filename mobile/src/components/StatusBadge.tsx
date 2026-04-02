import React from "react";
import { View, Text, StyleSheet } from "react-native";

type Status = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

const STATUS_CONFIG: Record<Status, { label: string; bg: string; text: string }> = {
  PENDING:    { label: "대기중",  bg: "#DBEAFE", text: "#1D4ED8" },
  PROCESSING: { label: "처리중",  bg: "#FEF3C7", text: "#92400E" },
  COMPLETED:  { label: "완료",    bg: "#D1FAE5", text: "#065F46" },
  FAILED:     { label: "실패",    bg: "#FEE2E2", text: "#991B1B" },
};

interface Props {
  status: string;
}

export default function StatusBadge({ status }: Props) {
  const cfg = STATUS_CONFIG[status as Status] ?? {
    label: status,
    bg: "#F3F4F6",
    text: "#374151",
  };

  return (
    <View style={[styles.badge, { backgroundColor: cfg.bg }]}>
      <Text style={[styles.text, { color: cfg.text }]}>{cfg.label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
    alignSelf: "flex-start",
  },
  text: {
    fontSize: 11,
    fontWeight: "600",
  },
});
