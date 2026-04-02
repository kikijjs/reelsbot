import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import { getDayDetail, getMonthlyCalendar } from "../api/client";
import { DayEntry } from "../types";
import JobCard from "./JobCard";

const STATUS_COLOR: Record<string, string> = {
  PENDING: "#3B82F6",
  PROCESSING: "#F59E0B",
  COMPLETED: "#10B981",
  FAILED: "#EF4444",
};

export default function CalendarView() {
  const [current, setCurrent] = useState(dayjs());
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  const { data: monthData } = useQuery({
    queryKey: ["calendar", current.year(), current.month() + 1],
    queryFn: () => getMonthlyCalendar(current.year(), current.month() + 1),
  });

  const { data: dayData } = useQuery({
    queryKey: ["day", selectedDate],
    queryFn: () => getDayDetail(selectedDate!),
    enabled: !!selectedDate,
  });

  const dayMap = new Map<string, DayEntry>(
    (monthData?.days ?? []).map((d: DayEntry) => [d.date, d])
  );

  // 월 그리드 생성
  const startOfMonth = current.startOf("month");
  const daysInMonth = current.daysInMonth();
  const startDow = startOfMonth.day(); // 0=일

  const cells: (number | null)[] = [
    ...Array(startDow).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];

  return (
    <div className="p-4">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-4">
        <button onClick={() => setCurrent(current.subtract(1, "month"))} className="px-3 py-1 rounded bg-gray-100 hover:bg-gray-200">◀</button>
        <h2 className="text-xl font-bold">{current.format("YYYY년 M월")}</h2>
        <button onClick={() => setCurrent(current.add(1, "month"))} className="px-3 py-1 rounded bg-gray-100 hover:bg-gray-200">▶</button>
      </div>

      {/* 요일 헤더 */}
      <div className="grid grid-cols-7 text-center text-sm font-medium text-gray-500 mb-1">
        {["일", "월", "화", "수", "목", "금", "토"].map((d) => <div key={d}>{d}</div>)}
      </div>

      {/* 날짜 그리드 */}
      <div className="grid grid-cols-7 gap-1">
        {cells.map((day, idx) => {
          if (!day) return <div key={`empty-${idx}`} />;
          const dateStr = current.date(day).format("YYYY-MM-DD");
          const entry = dayMap.get(dateStr);
          const isSelected = selectedDate === dateStr;

          return (
            <div
              key={dateStr}
              onClick={() => setSelectedDate(dateStr)}
              className={`
                relative h-14 rounded-lg cursor-pointer flex flex-col items-center justify-start pt-1
                border-2 transition-all
                ${isSelected ? "border-blue-500 bg-blue-50" : "border-transparent hover:bg-gray-50"}
              `}
            >
              <span className="text-sm font-medium">{day}</span>
              {entry && (
                <div className="flex gap-0.5 mt-0.5 flex-wrap justify-center">
                  {Object.entries(entry.status_counts).map(([status, count]) => (
                    <span
                      key={status}
                      className="text-white text-xs rounded-full px-1 leading-4"
                      style={{ backgroundColor: STATUS_COLOR[status] }}
                    >
                      {count}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* 범례 */}
      <div className="flex gap-4 mt-3 text-sm flex-wrap">
        {Object.entries(STATUS_COLOR).map(([s, c]) => (
          <span key={s} className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: c }} />
            {s}
          </span>
        ))}
      </div>

      {/* 선택된 날짜 상세 */}
      {selectedDate && dayData && (
        <div className="mt-6">
          <h3 className="font-semibold text-gray-700 mb-3">{selectedDate} 예약 목록</h3>
          {dayData.jobs.length === 0
            ? <p className="text-gray-400 text-sm">예약된 항목이 없습니다.</p>
            : dayData.jobs.map((j: any) => <JobCard key={j.id} summary={j} />)
          }
        </div>
      )}
    </div>
  );
}
