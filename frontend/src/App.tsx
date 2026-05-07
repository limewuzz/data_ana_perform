import type { ReactElement } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import { AppShell } from "@/components/layout/AppShell";
import { useSessionStore } from "@/store/session";
import DashboardPage from "@/pages/Dashboard";
import ExportsPage from "@/pages/Exports";
import LoginPage from "@/pages/Login";
import ModelSettingsPage from "@/pages/ModelSettings";
import OverviewPage from "@/pages/Overview";
import ReviewPage from "@/pages/Review";
import TasksPage from "@/pages/Tasks";
import AnnotatePage from "@/pages/Annotate";
import UserSettingsPage from "@/pages/UserSettings";

function ProtectedRoute({ children }: { children: ReactElement }) {
  const token = useSessionStore((state) => state.token);
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <AppShell>
                <Routes>
                  <Route path="/" element={<OverviewPage />} />
                  <Route path="/tasks" element={<TasksPage />} />
                  <Route path="/annotate" element={<AnnotatePage />} />
                  <Route path="/review" element={<ReviewPage />} />
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/exports" element={<ExportsPage />} />
                  <Route path="/settings/models" element={<ModelSettingsPage />} />
                  <Route path="/settings/users" element={<UserSettingsPage />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </AppShell>
            </ProtectedRoute>
          }
        />
      </Routes>
      <Toaster richColors theme="dark" position="top-right" />
    </>
  );
}
