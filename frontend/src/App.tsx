import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "./store/auth";
import { api } from "./api/endpoints";
import Sidebar from "./components/Sidebar";
import Login from "./pages/Login";
import AuthCallback from "./pages/AuthCallback";
import TelegramAuthCallback from "./pages/TelegramAuthCallback";
import SetupProfile from "./pages/SetupProfile";
import RoomsHub from "./pages/RoomsHub";
import Tournament from "./pages/Tournament";
import Tour from "./pages/Tour";
import PredictMatch from "./pages/PredictMatch";
import MatchPredictions from "./pages/MatchPredictions";
import PlayerProfile from "./pages/PlayerProfile";
import Profile from "./pages/Profile";
import RoomAdmin from "./pages/admin/RoomAdmin";
import Admin from "./pages/admin/Admin";

function Protected({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="p-8 text-slate-500">Загрузка…</div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (!user.nickname) return <Navigate to="/setup-profile" replace />;
  return children;
}

function Shell({ children }: { children: JSX.Element }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 pb-20 md:pb-0 md:pl-60">
        <div className="mx-auto max-w-5xl p-4">{children}</div>
      </main>
    </div>
  );
}

const page = (el: JSX.Element) => (
  <Protected>
    <Shell>{el}</Shell>
  </Protected>
);

// Entry point after login: jump straight to the last opened competition (or the
// only one), falling back to the hub when there is a choice to make.
function RootRedirect() {
  const { data, isLoading } = useQuery({
    queryKey: ["my-rooms"],
    queryFn: api.myRooms,
  });
  if (isLoading) return <div className="p-8 text-slate-500">Загрузка…</div>;
  const rooms = (data || []).filter((rm) => rm.is_active);
  const last = localStorage.getItem("last_room_id");
  const target = rooms.find((rm) => rm.id === last) ?? (rooms.length === 1 ? rooms[0] : null);
  return <Navigate to={target ? `/room/${target.id}` : "/rooms"} replace />;
}

export default function App() {
  const loadMe = useAuth((s) => s.loadMe);
  useEffect(() => {
    loadMe();
  }, [loadMe]);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="/telegram-auth" element={<TelegramAuthCallback />} />
      <Route path="/setup-profile" element={<SetupProfile />} />

      <Route
        path="/"
        element={
          <Protected>
            <RootRedirect />
          </Protected>
        }
      />
      <Route path="/rooms" element={page(<RoomsHub />)} />
      <Route path="/profile" element={page(<Profile />)} />
      <Route path="/admin/*" element={page(<Admin />)} />

      <Route path="/room/:roomId" element={page(<Tournament />)} />
      <Route path="/room/:roomId/tour/:date" element={page(<Tour />)} />
      <Route path="/room/:roomId/match/:id/predict" element={page(<PredictMatch />)} />
      <Route path="/room/:roomId/match/:id/predictions" element={page(<MatchPredictions />)} />
      <Route path="/room/:roomId/player/:userId" element={page(<PlayerProfile />)} />
      <Route path="/room/:roomId/admin/*" element={page(<RoomAdmin />)} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
