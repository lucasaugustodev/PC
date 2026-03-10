import { Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { BoardProvider } from "./contexts/BoardContext";
import { Layout } from "./components/Layout";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { BoardListPage } from "./pages/BoardListPage";
import { BoardDashboard } from "./pages/BoardDashboard";
import { DesktopPage } from "./pages/DesktopPage";
import { LauncherPage } from "./pages/LauncherPage";
import { SettingsPage } from "./pages/SettingsPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return <div className="flex h-screen items-center justify-center text-muted-foreground">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  const { user, isLoading } = useAuth();
  if (isLoading) return <div className="flex h-screen items-center justify-center text-muted-foreground">Loading...</div>;

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/register" element={user ? <Navigate to="/" replace /> : <RegisterPage />} />
      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<BoardListPage />} />
        <Route path="boards/:boardId" element={<BoardDashboard />} />
        <Route path="boards/:boardId/desktop" element={<DesktopPage />} />
        <Route path="boards/:boardId/launcher" element={<LauncherPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BoardProvider>
        <AppRoutes />
      </BoardProvider>
    </AuthProvider>
  );
}
