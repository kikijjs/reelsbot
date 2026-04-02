export type JobStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
export type Platform = "instagram" | "youtube" | "tiktok";

export interface Job {
  id: string;
  instagram_url: string;
  platform: Platform;
  status: JobStatus;
  gemini_analysis: Record<string, unknown> | null;
  script: Script5Parts | null;
  script_variant_b: Script5Parts | null;
  downloaded_video_path: string | null;
  tts_audio_path: string | null;
  final_video_path: string | null;
  scheduled_at: string | null;
  uploaded_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface Script5Parts {
  cover_text: string;
  hook: string;
  body: string;
  cta: string;
  subtitle_timeline: SubtitleCue[];
}

export interface SubtitleCue {
  text: string;
  start_sec: number;
  end_sec: number;
}

export interface DayEntry {
  date: string;
  count: number;
  status_counts: Partial<Record<JobStatus, number>>;
  dominant_color: string;
}

export interface MetricPoint {
  interval_hours: number;
  collected_at: string;
  views: number;
  likes: number;
  comments: number;
  shares: number;
}

export interface ScriptTemplate {
  id: string;
  name: string;
  script: Script5Parts;
  source_job_id: string | null;
  performance_score: number;
  created_at: string;
}
