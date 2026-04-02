import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

// 알림 수신 시 동작 설정: 앱이 포그라운드 상태여도 배너 + 소리 표시
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

/**
 * 푸시 알림 권한 요청 및 Expo Push Token 반환.
 * 실제 기기(물리적 iOS/Android)에서만 토큰을 발급받을 수 있습니다.
 * 시뮬레이터에서는 null을 반환합니다.
 */
export async function registerForPushNotificationsAsync(): Promise<string | null> {
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("default", {
      name: "default",
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: "#2563EB",
    });
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== "granted") {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== "granted") {
    console.warn("[push] 알림 권한이 거부되었습니다.");
    return null;
  }

  try {
    const tokenData = await Notifications.getExpoPushTokenAsync();
    console.log("[push] Expo Push Token:", tokenData.data);
    return tokenData.data;
  } catch (e) {
    // 시뮬레이터 또는 개발 빌드에서는 토큰 발급 실패 가능
    console.warn("[push] 토큰 발급 실패 (시뮬레이터?):", e);
    return null;
  }
}

/**
 * 로컬 알림 전송 (서버 없이 기기 내부에서 즉시 알림).
 * 작업 완료/실패 시 앱 내부에서 직접 호출 가능.
 */
export async function sendLocalNotification(
  title: string,
  body: string,
  data?: Record<string, unknown>
): Promise<void> {
  await Notifications.scheduleNotificationAsync({
    content: { title, body, data: data ?? {} },
    trigger: null, // 즉시 전송
  });
}

/**
 * 알림 클릭 리스너 등록.
 * 반환된 subscription은 컴포넌트 unmount 시 .remove() 호출 필요.
 */
export function addNotificationResponseListener(
  handler: (response: Notifications.NotificationResponse) => void
): Notifications.Subscription {
  return Notifications.addNotificationResponseReceivedListener(handler);
}
