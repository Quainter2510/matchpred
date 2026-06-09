import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./store/auth";
import { setAccessToken } from "./api/client";
import Sidebar from "./components/Sidebar";
import Login from "./pages/Login";
import AuthCallback from "./pages/AuthCallback";
import SetupProfile from "./pages/SetupProfile";
import TournamentJoin from "./pages/TournamentJoin";
import Tournament from "./pages/Tournament";
import Tour from "./pages/Tour";
import PredictMatch from "./pages/PredictMatch";
import MatchPredictions from "./pages/MatchPredictions";
import Profile from "./pages/Profile";
import TelegramAuthCallback from "./pages/TelegramAuthCallback";
import Admin from "./pages/admin/Admin";

function Protected({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="p-8 text-slate-500">Загрузка…</div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  // Player+ gate: must have joined the tournament (superadmin is implicitly in).
  if (!user.tournament_role && user.system_role !== "superadmin") {
    return <Navigate to="/tournament-join" replace />;
  }
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

export default function App() {
  const loadMe = useAuth((s) => s.loadMe);

  useEffect(() => {
    if (setAccessToken && localStorage.getItem("access_token")) {
      loadMe();
    } else {
      // Try a silent refresh via cookie.
      loadMe();
    }
  }, [loadMe]);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="/telegram-auth" element={<TelegramAuthCallback />} />
      <Route path="/setup-profile" element={<SetupProfile />} />
      <Route path="/tournament-join" element={<TournamentJoin />} />

      <Route
        path="/"
        element={
          <Protected>
            <Shell>
              <Tournament />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/tour/:date"
        element={
          <Protected>
            <Shell>
              <Tour />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/match/:id/predict"
        element={
          <Protected>
            <Shell>
              <PredictMatch />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/match/:id/predictions"
        element={
          <Protected>
            <Shell>
              <MatchPredictions />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/profile"
        element={
          <Protected>
            <Shell>
              <Profile />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/admin/*"
        element={
          <Protected>
            <Shell>
              <Admin />
            </Shell>
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
