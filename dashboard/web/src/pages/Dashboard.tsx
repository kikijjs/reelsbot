import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listJobs, getLeaderboard } from "../api/client";
import CalendarView from "../components/CalendarView";
import JobCard from "../components/JobCard";

export default function Dashboard() {
  const { data: jobsData } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => listJobs({ size: 5 }),
    refetchInterval: 10_000,   // 10초마다 갱신
  });
  const { data: leaderboard } = useQuery({
    queryKey: ["leaderboard"],
    queryFn: () => getLeaderboard(5),
  });

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">reelsbot 대시보드</h1>
        <Link to="/new" className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
          + 새 작업
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 캘린더 */}
        <div className="border rounded-2xl overflow-hidden bg-white shadow-sm">
          <div className="px-4 pt-4 pb-2 border-b">
            <h2 className="font-semibold">📅 업로드 캘린더</h2>
          </div>
          <CalendarView />
        </div>

        {/* 최근 작업 */}
        <div>
          <h2 className="font-semibold mb-3">⏱️ 최근 작업</h2>
          {(jobsData?.items ?? []).map((job: any) => (
            <Link key={job.id} to={`/jobs/${job.id}`}>
              <JobCard job={job} />
            </Link>
          ))}
        </div>
      </div>

      {/* 성과 리더보드 */}
      {leaderboard?.length > 0 && (
        <div>
          <h2 className="font-semibold mb-3">🏆 72h 조회수 리더보드</h2>
          <div className="border rounded-2xl overflow-hidden bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-500">
                <tr>
                  <th className="text-left px-4 py-2">커버 문구</th>
                  <th className="text-left px-4 py-2">플랫폼</th>
                  <th className="text-right px-4 py-2">조회수</th>
                  <th className="text-right px-4 py-2">좋아요</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((item: any, i: number) => (
                  <tr key={item.job_id} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-2 truncate max-w-xs">
                      {i + 1}. {item.cover_text ?? "—"}
                    </td>
                    <td className="px-4 py-2 capitalize">{item.platform}</td>
                    <td className="px-4 py-2 text-right font-medium">{item.views_72h.toLocaleString()}</td>
                    <td className="px-4 py-2 text-right">{item.likes_72h.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
