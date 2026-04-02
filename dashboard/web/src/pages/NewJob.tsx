import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createJob } from "../api/client";

export default function NewJob() {
  const nav = useNavigate();
  const [url, setUrl] = useState("");
  const [platform, setPlatform] = useState("instagram");
  const [scheduledAt, setScheduledAt] = useState("");
  const [abTest, setAbTest] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!url.trim()) { setError("Instagram URL을 입력해주세요."); return; }

    setLoading(true);
    try {
      const job = await createJob({
        instagram_url: url.trim(),
        platform,
        scheduled_at: scheduledAt || undefined,
        ab_test: abTest,
      });
      nav(`/jobs/${job.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-lg mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">새 작업 만들기</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Instagram URL *</label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.instagram.com/reel/..."
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">업로드 플랫폼</label>
          <select value={platform} onChange={(e) => setPlatform(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm">
            <option value="instagram">📸 Instagram Reels</option>
            <option value="youtube">▶️ YouTube Shorts</option>
            <option value="tiktok">🎵 TikTok</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">예약 업로드 시간 (선택)</label>
          <input
            type="datetime-local"
            value={scheduledAt}
            onChange={(e) => setScheduledAt(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm"
          />
        </div>

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="abtest"
            checked={abTest}
            onChange={(e) => setAbTest(e.target.checked)}
            className="w-4 h-4"
          />
          <label htmlFor="abtest" className="text-sm">A/B 테스트 모드 (스크립트 2버전 생성)</label>
        </div>

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white rounded-lg py-2.5 font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {loading ? "⏳ 분석 중..." : "🚀 작업 시작"}
        </button>
      </form>
    </div>
  );
}
