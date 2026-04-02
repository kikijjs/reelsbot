import { useState } from "react";
import dayjs from "dayjs";
import { Job } from "../types";

const STATUS_COLOR: Record<string, string> = {
  PENDING: "bg-blue-100 text-blue-800",
  PROCESSING: "bg-yellow-100 text-yellow-800",
  COMPLETED: "bg-green-100 text-green-800",
  FAILED: "bg-red-100 text-red-800",
};

const PLATFORM_ICON: Record<string, string> = {
  instagram: "📸",
  youtube: "▶️",
  tiktok: "🎵",
};

interface Props {
  summary?: any;   // 캘린더 축약형
  job?: Job;       // 전체 Job
  onDelete?: (id: string) => void;
  onEdit?: (id: string) => void;
}

export default function JobCard({ summary, job, onDelete, onEdit }: Props) {
  const [expanded, setExpanded] = useState(false);
  const data = job ?? summary;
  if (!data) return null;

  const statusClass = STATUS_COLOR[data.status] ?? "bg-gray-100 text-gray-800";
  const script = job?.script;

  return (
    <div className="border rounded-xl p-4 mb-3 bg-white shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">{PLATFORM_ICON[data.platform] ?? "🌐"}</span>
          <div>
            <p className="font-semibold text-sm truncate max-w-xs">
              {data.cover_text ?? script?.cover_text ?? "커버 문구 없음"}
            </p>
            <p className="text-xs text-gray-400">
              {data.scheduled_at ? dayjs(data.scheduled_at).format("YYYY-MM-DD HH:mm") : "미예약"}
            </p>
          </div>
        </div>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusClass}`}>
          {data.status}
        </span>
      </div>

      {/* 확장 영역 */}
      {job && (
        <button
          className="mt-2 text-xs text-blue-500 hover:underline"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? "접기 ▲" : "자세히 보기 ▼"}
        </button>
      )}

      {expanded && job && (
        <div className="mt-3 text-sm space-y-2 border-t pt-3">
          {job.final_video_path && (
            <video
              src={`/media/${job.final_video_path.split("/media/")[1]}`}
              controls
              className="w-full max-w-xs rounded-lg"
            />
          )}
          {script && (
            <div className="space-y-1">
              <p><span className="font-medium">후킹:</span> {script.hook}</p>
              <p><span className="font-medium">본문:</span> {script.body}</p>
              <p><span className="font-medium">CTA:</span> {script.cta}</p>
            </div>
          )}
          {job.error_message && (
            <p className="text-red-500 text-xs">오류: {job.error_message}</p>
          )}
          <div className="flex gap-2 pt-1">
            {onEdit && (
              <button onClick={() => onEdit(job.id)} className="text-xs px-3 py-1 rounded bg-blue-50 text-blue-600 hover:bg-blue-100">
                예약 수정
              </button>
            )}
            {onDelete && (
              <button onClick={() => onDelete(job.id)} className="text-xs px-3 py-1 rounded bg-red-50 text-red-600 hover:bg-red-100">
                삭제
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
