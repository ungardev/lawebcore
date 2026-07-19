import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from '@/features/auth/AuthProvider';
import { ProtectedRoute } from '@/features/auth/ProtectedRoute';
import { AppLayout } from '@/components/layout/AppLayout';

import { LoginPage } from '@/features/auth/LoginPage';
import { DashboardPage } from '@/features/dashboard/DashboardPage';
import { CampaignsListPage } from '@/features/campaigns/CampaignsListPage';
import { CampaignDetailPage } from '@/features/campaigns/CampaignDetailPage';
import { CampaignKanbanPage } from '@/features/campaigns/CampaignKanbanPage';
import { ClientsPage } from '@/features/clients/ClientsPage';
import { LensChatPage } from '@/features/lens/pages/LensChatPage';
import { LensRunsListPage } from '@/features/lens/pages/LensRunsListPage';
import { LensSearchPage } from '@/features/lens/pages/LensSearchPage';
import { SettingsPage } from '@/features/settings/SettingsPage';

function Redirect({ to }: { to: string }) {
  return <Navigate to={to} replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/home" replace />} />
          <Route path="home" element={<DashboardPage />} />
          <Route path="campaigns" element={<CampaignsListPage />} />
          <Route path="campaigns/kanban" element={<CampaignKanbanPage />} />
          <Route path="campaigns/:id" element={<CampaignDetailPage />} />
          <Route path="clients" element={<ClientsPage />} />
          <Route path="influencer-lens" element={<LensChatPage />} />
          <Route path="influencer-lens/:id" element={<LensChatPage />} />
          <Route path="influencer-lens/runs" element={<LensRunsListPage />} />
          <Route path="influencer-lens/search" element={<LensSearchPage />} />
          <Route path="settings" element={<SettingsPage />} />

          <Route path="dashboard" element={<Redirect to="/home" />} />
          <Route path="influencers" element={<Redirect to="/influencer-lens" />} />
          <Route path="ai" element={<Redirect to="/influencer-lens" />} />
          <Route path="brands" element={<Redirect to="/home" />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
