import React, { useState } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Modal,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import CalendarView from "../components/CalendarView";
import StatusBadge from "../components/StatusBadge";
import type { DayEntry } from "../api/client";
import type { RootStackParamList } from "../navigation/types";

type Nav = NativeStackNavigationProp<RootStackParamList, "Calendar">;

const PLATFORM_ICON: Record<string, string> = {
  instagram: "📸",
  youtube: "▶️",
  tiktok: "🎵",
};

export default function CalendarScreen() {
  const nav = useNavigation<Nav>();
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [dayEntries, setDayEntries] = useState<DayEntry[]>([]);
  const [modalVisible, setModalVisible] = useState(false);

  const handleDayPress = (date: string, entries: DayEntry[]) => {
    setSelectedDate(date);
    setDayEntries(entries);
    if (entries.length > 0) setModalVisible(true);
  };

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.title}>📅 업로드 캘린더</Text>

        <CalendarView onDayPress={handleDayPress} />

        {/* 범례 */}
        <View style={styles.legend}>
          {[
            { label: "대기중", color: "#3B82F6" },
            { label: "처리중", color: "#F59E0B" },
            { label: "완료",   color: "#10B981" },
            { label: "실패",   color: "#EF4444" },
          ].map((item) => (
            <View key={item.label} style={styles.legendItem}>
              <View style={[styles.dot, { backgroundColor: item.color }]} />
              <Text style={styles.legendText}>{item.label}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* 날짜 선택 시 모달 */}
      <Modal
        visible={modalVisible}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setModalVisible(false)}
      >
        <SafeAreaView style={styles.modalSafe}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>{selectedDate} 작업 목록</Text>
            <TouchableOpacity onPress={() => setModalVisible(false)}>
              <Text style={styles.modalClose}>닫기</Text>
            </TouchableOpacity>
          </View>

          <FlatList
            data={dayEntries}
            keyExtractor={(item) => item.job_id}
            contentContainerStyle={styles.modalList}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={styles.entryRow}
                onPress={() => {
                  setModalVisible(false);
                  nav.navigate("JobDetail", { jobId: item.job_id });
                }}
                activeOpacity={0.7}
              >
                <Text style={styles.entryIcon}>
                  {PLATFORM_ICON[item.platform] ?? "📱"}
                </Text>
                <Text style={styles.entryCover} numberOfLines={1}>
                  {item.cover_text ?? "—"}
                </Text>
                <StatusBadge status={item.status} />
              </TouchableOpacity>
            )}
          />
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#F9FAFB" },
  container: { flex: 1, padding: 16 },
  title: { fontSize: 20, fontWeight: "700", color: "#111827", marginBottom: 16 },
  legend: { flexDirection: "row", justifyContent: "center", gap: 16, marginTop: 12 },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 4 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  legendText: { fontSize: 11, color: "#6B7280" },

  modalSafe: { flex: 1, backgroundColor: "#F9FAFB" },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 16,
    borderBottomWidth: 1,
    borderColor: "#E5E7EB",
    backgroundColor: "#FFFFFF",
  },
  modalTitle: { fontSize: 16, fontWeight: "700", color: "#111827" },
  modalClose: { fontSize: 14, color: "#2563EB", fontWeight: "600" },
  modalList: { padding: 16, gap: 10 },
  entryRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 12,
    gap: 10,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 1,
  },
  entryIcon: { fontSize: 18 },
  entryCover: { flex: 1, fontSize: 13, color: "#374151" },
});
