import axios from "axios";

// 개발 환경: 로컬 FastAPI 서버
// 실제 기기 테스트 시 localhost 대신 PC IP 주소 사용 (예: 192.168.0.10)
const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

// ── 타입 정의 ─────────────────────────────────────────────────────────────

export interface Job {
  id: string;
  instagram_url: string;
  platform: "instagram" | "youtube" | "tiktok";
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  scheduled_at: string | null;
  ab_test: boolean;
  final_video_path: string | null;
  post_url: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface SubtitleCue {
  text: string;
  start_sec: number;
  end_sec: number;
}

export interface Script5Parts {
  cover_text: string;
  hook: string;
  body: string;
  cta: string;
  subtitle_timeline: SubtitleCue[];
}

export interface MetricPoint {
  interval_hours: number;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  collected_at: string;
}

export interface DayEntry {
  job_id: string;
  platform: string;
  status: string;
  color: string;
  cover_text: string | null;
}

export interface ScriptTemplate {
  id: string;
  name: string;
  script: Record<string, unknown>;
  performance_score: number;
  created_at: string;
}

export interface LeaderboardItem {
  job_id: string;
  platform: string;
  cover_text: string | null;
  views_72h: number;
  likes_72h: number;
  score: number;
}

// ── 작업(Job) API ─────────────────────────────────────────────────────────

export async function listJobs(params?: {
  status?: string;
  platform?: string;
  page?: number;
  size?: number;
}): Promise<{ items: Job[]; total: number; page: number; size: number }> {
  const res = await api.get("/jobs/", { params });
  return res.data;
}

export async function getJob(id: string): Promise<Job & { script: Script5Parts | null; script_variant_b: Script5Parts | null }> {
  const res = await api.get(`/jobs/${id}`);
  return res.data;
}

export async function createJob(payload: {
  instagram_url: string;
  platform: string;
  scheduled_at?: string;
  ab_test?: boolean;
}): Promise<Job> {
  const res = await api.post("/jobs/", payload);
  return res.data;
}

export async function deleteJob(id: string): Promise<void> {
  await api.delete(`/jobs/${id}`);
}

// ── 캘린더 API ────────────────────────────────────────────────────────────

export async function getMonthlyCalendar(year: number, month: number): Promise<Record<string, DayEntry[]>> {
  const res = await api.get("/calendar/monthly", { params: { year, month } });
  return res.data;
}

export async function getDayJobs(date: string): Promise<DayEntry[]> {
  const res = await api.get("/calendar/day", { params: { date } });
  return res.data;
}

// ── 분석(Analytics) API ──────────────────────────────────────────────────

export async function getJobAnalytics(jobId: string): Promise<{ metrics: MetricPoint[] }> {
  const res = await api.get(`/analytics/${jobId}`);
  return res.data;
}

export async function getLeaderboard(limit = 10): Promise<LeaderboardItem[]> {
  const res = await api.get("/analytics/leaderboard", { params: { limit } });
  return res.data;
}

// ── 템플릿 API ────────────────────────────────────────────────────────────

export async function listTemplates(): Promise<ScriptTemplate[]> {
  const res = await api.get("/templates/");
  return res.data;
}

export default api;
