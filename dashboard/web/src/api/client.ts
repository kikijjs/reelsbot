import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const api = axios.create({ baseURL: BASE_URL });

// ── Jobs ─────────────────────────────────────────────────────────

export const createJob = (data: {
  instagram_url: string;
  platform: string;
  scheduled_at?: string;
  ab_test?: boolean;
}) => api.post("/jobs/", data).then((r) => r.data);

export const listJobs = (params: { page?: number; size?: number; status?: string; platform?: string }) =>
  api.get("/jobs/", { params }).then((r) => r.data);

export const getJob = (id: string) => api.get(`/jobs/${id}`).then((r) => r.data);

export const patchJob = (id: string, data: { scheduled_at?: string; platform?: string }) =>
  api.patch(`/jobs/${id}`, data).then((r) => r.data);

export const deleteJob = (id: string) => api.delete(`/jobs/${id}`);

// ── Calendar ─────────────────────────────────────────────────────

export const getMonthlyCalendar = (year: number, month: number) =>
  api.get("/calendar/monthly", { params: { year, month } }).then((r) => r.data);

export const getDayDetail = (date: string) =>
  api.get("/calendar/day", { params: { date } }).then((r) => r.data);

// ── Analytics ────────────────────────────────────────────────────

export const getJobAnalytics = (jobId: string) =>
  api.get(`/analytics/${jobId}`).then((r) => r.data);

export const getLeaderboard = (limit = 10) =>
  api.get("/analytics/leaderboard", { params: { limit } }).then((r) => r.data);

// ── Templates ────────────────────────────────────────────────────

export const listTemplates = () => api.get("/templates/").then((r) => r.data);

export const saveTemplateFromJob = (jobId: string, name: string) =>
  api.post(`/templates/from-job/${jobId}`, null, { params: { name } }).then((r) => r.data);

export const deleteTemplate = (id: string) => api.delete(`/templates/${id}`);
