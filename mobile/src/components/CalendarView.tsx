import React, { useState } from "react";
import { View, ActivityIndicator, StyleSheet } from "react-native";
import { Calendar, DateData } from "react-native-calendars";
import { useQuery } from "@tanstack/react-query";
import { getMonthlyCalendar, DayEntry } from "../api/client";

const STATUS_COLOR: Record<string, string> = {
  PENDING:    "#3B82F6",
  PROCESSING: "#F59E0B",
  COMPLETED:  "#10B981",
  FAILED:     "#EF4444",
};

interface Props {
  onDayPress: (date: string, entries: DayEntry[]) => void;
}

export default function CalendarView({ onDayPress }: Props) {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);

  const { data, isLoading } = useQuery({
    queryKey: ["calendar", year, month],
    queryFn: () => getMonthlyCalendar(year, month),
  });

  // react-native-calendars markedDates 형식으로 변환
  const markedDates: Record<string, { dots: { key: string; color: string }[] }> = {};

  if (data) {
    for (const [dateStr, entries] of Object.entries(data)) {
      const dots = (entries as DayEntry[]).slice(0, 4).map((e, i) => ({
        key: `${e.job_id}_${i}`,
        color: STATUS_COLOR[e.status] ?? "#9CA3AF",
      }));
      markedDates[dateStr] = { dots };
    }
  }

  const handleMonthChange = (monthData: DateData) => {
    setYear(monthData.year);
    setMonth(monthData.month);
  };

  const handleDayPress = (day: DateData) => {
    const entries = data?.[day.dateString] ?? [];
    onDayPress(day.dateString, entries as DayEntry[]);
  };

  return (
    <View style={styles.container}>
      {isLoading && (
        <ActivityIndicator
          style={StyleSheet.absoluteFill}
          color="#2563EB"
        />
      )}
      <Calendar
        markingType="multi-dot"
        markedDates={markedDates}
        onDayPress={handleDayPress}
        onMonthChange={handleMonthChange}
        theme={{
          todayTextColor: "#2563EB",
          arrowColor: "#2563EB",
          dotStyle: { marginTop: 2 },
        }}
        style={styles.calendar}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    overflow: "hidden",
  },
  calendar: {
    borderRadius: 16,
  },
});
