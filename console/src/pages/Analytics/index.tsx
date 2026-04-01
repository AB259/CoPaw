import { Routes, Route, Navigate } from "react-router-dom";
import OverviewPage from "./Overview";
import UsersPage from "./Users";
import SessionsPage from "./Sessions";
import MessagesPage from "./Messages";

export default function AnalyticsPage() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="overview" replace />} />
      <Route path="overview" element={<OverviewPage />} />
      <Route path="users" element={<UsersPage />} />
      <Route path="sessions" element={<SessionsPage />} />
      <Route path="messages" element={<MessagesPage />} />
    </Routes>
  );
}
