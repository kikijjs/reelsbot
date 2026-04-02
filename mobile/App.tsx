import React, { useEffect, useRef } from "react";
import { Platform } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as Notifications from "expo-notifications";

import HomeScreen from "./src/screens/HomeScreen";
import CalendarScreen from "./src/screens/CalendarScreen";
import JobDetailScreen from "./src/screens/JobDetailScreen";
import AnalyticsScreen from "./src/screens/AnalyticsScreen";
import {
  registerForPushNotificationsAsync,
  addNotificationResponseListener,
} from "./src/notifications/push";
import type { RootStackParamList } from "./src/navigation/types";

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator<RootStackParamList>();
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 10_000, retry: 1 },
  },
});

// 탭 아이콘 텍스트 (이모지로 단순하게)
const TAB_ICONS: Record<string, string> = {
  홈: "🎬",
  캘린더: "📅",
};

function TabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarIcon: ({ focused }) => {
          const icon = TAB_ICONS[route.name] ?? "•";
          return <React.Fragment>{/* icon rendered via tabBarLabel */}</React.Fragment>;
        },
        tabBarLabel: ({ focused, color }) => {
          const icon = TAB_ICONS[route.name] ?? "";
          const { Text } = require("react-native");
          return (
            <Text style={{ fontSize: 10, color, marginTop: -4 }}>
              {icon} {route.name}
            </Text>
          );
        },
        tabBarActiveTintColor: "#2563EB",
        tabBarInactiveTintColor: "#9CA3AF",
        tabBarStyle: {
          backgroundColor: "#FFFFFF",
          borderTopColor: "#E5E7EB",
          paddingBottom: Platform.OS === "ios" ? 20 : 6,
          height: Platform.OS === "ios" ? 80 : 58,
        },
      })}
    >
      <Tab.Screen name="홈" component={HomeScreen} />
      <Tab.Screen name="캘린더" component={CalendarScreen} />
    </Tab.Navigator>
  );
}

export default function App() {
  const navigationRef = useRef<any>(null);
  const notifListenerRef = useRef<Notifications.Subscription | null>(null);

  useEffect(() => {
    // 푸시 알림 권한 요청
    registerForPushNotificationsAsync().catch(console.warn);

    // 알림 클릭 시 해당 JobDetail로 이동
    notifListenerRef.current = addNotificationResponseListener((response) => {
      const data = response.notification.request.content.data as any;
      if (data?.jobId && navigationRef.current) {
        navigationRef.current.navigate("JobDetail", { jobId: data.jobId });
      }
    });

    return () => {
      notifListenerRef.current?.remove();
    };
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <SafeAreaProvider>
        <NavigationContainer ref={navigationRef}>
          <Stack.Navigator screenOptions={{ headerShown: false }}>
            {/* 탭 기반 메인 화면 */}
            <Stack.Screen name="Home" component={TabNavigator} />
            {/* 스택 전환 화면 */}
            <Stack.Screen
              name="JobDetail"
              component={JobDetailScreen}
              options={{ headerShown: false }}
            />
            <Stack.Screen
              name="Analytics"
              component={AnalyticsScreen}
              options={{
                headerShown: true,
                title: "성과 분석",
                headerTintColor: "#2563EB",
                headerTitleStyle: { fontWeight: "700" },
              }}
            />
          </Stack.Navigator>
        </NavigationContainer>
      </SafeAreaProvider>
    </QueryClientProvider>
  );
}
