import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  Switch,
  ScrollView,
  StyleSheet,
  Alert,
  ActivityIndicator,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { createJob } from "../api/client";
import type { RootStackParamList } from "../navigation/types";

const PLATFORM_OPTIONS = [
  { value: "instagram", label: "📸 Instagram Reels" },
  { value: "youtube",   label: "▶️ YouTube Shorts" },
  { value: "tiktok",    label: "🎵 TikTok" },
];

type Nav = NativeStackNavigationProp<RootStackParamList, "Home">;

export default function HomeScreen() {
  const nav = useNavigation<Nav>();
  const [url, setUrl] = useState("");
  const [platform, setPlatform] = useState("instagram");
  const [abTest, setAbTest] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleStart = async () => {
    if (!url.trim()) {
      Alert.alert("입력 오류", "Instagram URL을 입력해주세요.");
      return;
    }
    if (!url.includes("instagram.com")) {
      Alert.alert("입력 오류", "Instagram URL 형식이 올바르지 않습니다.");
      return;
    }

    setLoading(true);
    try {
      const job = await createJob({
        instagram_url: url.trim(),
        platform,
        ab_test: abTest,
      });
      Alert.alert("작업 시작!", `작업 ID: ${job.id.slice(0, 8)}...`, [
        { text: "확인", onPress: () => nav.navigate("JobDetail", { jobId: job.id }) },
      ]);
      setUrl("");
    } catch (err: any) {
      const msg = err.response?.data?.detail ?? "오류가 발생했습니다.";
      Alert.alert("오류", msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>🎬 새 작업 만들기</Text>
        <Text style={styles.subtitle}>Instagram Reel URL을 입력하면 자동으로 편집 후 업로드합니다.</Text>

        {/* URL 입력 */}
        <View style={styles.field}>
          <Text style={styles.label}>Instagram URL *</Text>
          <TextInput
            style={styles.input}
            value={url}
            onChangeText={setUrl}
            placeholder="https://www.instagram.com/reel/..."
            placeholderTextColor="#9CA3AF"
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
          />
        </View>

        {/* 플랫폼 선택 */}
        <View style={styles.field}>
          <Text style={styles.label}>업로드 플랫폼</Text>
          <View style={styles.platformRow}>
            {PLATFORM_OPTIONS.map((opt) => (
              <TouchableOpacity
                key={opt.value}
                style={[styles.platformBtn, platform === opt.value && styles.platformBtnActive]}
                onPress={() => setPlatform(opt.value)}
                activeOpacity={0.7}
              >
                <Text style={[styles.platformText, platform === opt.value && styles.platformTextActive]}>
                  {opt.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* A/B 테스트 */}
        <View style={styles.toggleRow}>
          <View>
            <Text style={styles.label}>A/B 테스트 모드</Text>
            <Text style={styles.hint}>스크립트 2가지 버전 생성</Text>
          </View>
          <Switch
            value={abTest}
            onValueChange={setAbTest}
            trackColor={{ false: "#D1D5DB", true: "#93C5FD" }}
            thumbColor={abTest ? "#2563EB" : "#F9FAFB"}
          />
        </View>

        {/* 시작 버튼 */}
        <TouchableOpacity
          style={[styles.btn, loading && styles.btnDisabled]}
          onPress={handleStart}
          disabled={loading}
          activeOpacity={0.8}
        >
          {loading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.btnText}>🚀 작업 시작</Text>
          )}
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#F9FAFB" },
  container: { padding: 20, paddingBottom: 40 },
  title: { fontSize: 24, fontWeight: "700", color: "#111827", marginBottom: 6 },
  subtitle: { fontSize: 13, color: "#6B7280", marginBottom: 24, lineHeight: 18 },
  field: { marginBottom: 20 },
  label: { fontSize: 13, fontWeight: "600", color: "#374151", marginBottom: 6 },
  hint: { fontSize: 11, color: "#6B7280", marginTop: 2 },
  input: {
    borderWidth: 1,
    borderColor: "#D1D5DB",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: Platform.OS === "ios" ? 12 : 8,
    fontSize: 14,
    color: "#111827",
    backgroundColor: "#FFFFFF",
  },
  platformRow: { flexDirection: "column", gap: 8 },
  platformBtn: {
    borderWidth: 1,
    borderColor: "#D1D5DB",
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 14,
    backgroundColor: "#FFFFFF",
  },
  platformBtnActive: { borderColor: "#2563EB", backgroundColor: "#EFF6FF" },
  platformText: { fontSize: 14, color: "#374151" },
  platformTextActive: { color: "#1D4ED8", fontWeight: "600" },
  toggleRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 14,
    marginBottom: 24,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 1,
  },
  btn: {
    backgroundColor: "#2563EB",
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
  },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: "#FFFFFF", fontSize: 16, fontWeight: "700" },
});
