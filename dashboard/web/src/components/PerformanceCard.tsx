import { useQuery } from "@tanstack/react-query";
import { getJobAnalytics } from "../api/client";
import { MetricPoint } from "../types";

interface Props {
  jobId: string;
}

export default function PerformanceCard({ jobId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics", jobId],
    queryFn: () => getJobAnalytics(jobId),
  });

  if (isLoading) return <div className="text-sm text-gray-400">성과 데이터 로딩 중...</div>;
  if (!data?.metrics?.length) return <div className="text-sm text-gray-400">아직 성과 데이터가 없습니다.</div>;

  return (
    <div className="border rounded-xl p-4 bg-white shadow-sm">
      <h4 className="font-semibold text-sm mb-3">📊 성과 지표</h4>
      <div className="grid grid-cols-2 gap-3">
        {(data.metrics as MetricPoint[]).map((m) => (
          <div key={m.interval_hours} className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500 font-medium mb-2">{m.interval_hours}h 후</p>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">👁️ 조회</span>
                <span className="font-bold">{m.views.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">❤️ 좋아요</span>
                <span className="font-bold">{m.likes.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">💬 댓글</span>
                <span className="font-bold">{m.comments.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">↗️ 공유</span>
                <span className="font-bold">{m.shares.toLocaleString()}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
