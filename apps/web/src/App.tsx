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
import { BrandsPage } from '@/features/brands/BrandsPage';
import { InfluencersPage } from '@/features/influencers/InfluencersPage';
import { AIAssistantPage } from '@/features/ai-assistant/AIAssistantPage';
import { SettingsPage } from '@/features/settings/SettingsPage';

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
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="campaigns" element={<CampaignsListPage />} />
          <Route path="campaigns/kanban" element={<CampaignKanbanPage />} />
          <Route path="campaigns/:id" element={<CampaignDetailPage />} />
          <Route path="clients" element={<ClientsPage />} />
          <Route path="brands" element={<BrandsPage />} />
          <Route path="influencers" element={<InfluencersPage />} />
          <Route path="ai" element={<AIAssistantPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}