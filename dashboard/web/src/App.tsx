import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import NewJob from "./pages/NewJob";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5_000 } },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          <nav className="bg-white border-b px-6 py-3 flex items-center gap-6">
            <span className="font-bold text-blue-600 text-lg">🎬 reelsbot</span>
            <NavLink to="/" className={({ isActive }) => `text-sm font-medium ${isActive ? "text-blue-600" : "text-gray-600 hover:text-gray-900"}`}>
              대시보드
            </NavLink>
            <NavLink to="/new" className={({ isActive }) => `text-sm font-medium ${isActive ? "text-blue-600" : "text-gray-600 hover:text-gray-900"}`}>
              새 작업
            </NavLink>
          </nav>
          <main>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/new" element={<NewJob />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
