import { createBrowserRouter, Navigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import { ArchiveShell } from '../components/layout/ArchiveShell';
import { RequireRole } from '../components/common/RequireRole';
import { LoginPage } from '../pages/Login';
import { CandidatesPage } from '../pages/Candidates';
import { ClustersPage } from '../pages/Clusters';
import { GoldenPage } from '../pages/Golden';
import { RulesPage } from '../pages/Rules';
import { RunReportPage } from '../pages/RunReport';
import { requireAuth } from './guards';

const shell = (element: ReactNode) => <ArchiveShell>{element}</ArchiveShell>;

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    loader: requireAuth,
    element: <Navigate to="/candidates" replace />,
  },
  {
    path: '/candidates',
    loader: requireAuth,
    element: shell(<CandidatesPage />),
  },
  {
    path: '/clusters',
    loader: requireAuth,
    element: shell(<ClustersPage />),
  },
  {
    path: '/golden',
    loader: requireAuth,
    element: shell(<GoldenPage />),
  },
  {
    path: '/rules',
    loader: requireAuth,
    element: shell(<RulesPage />),
  },
  {
    path: '/runs',
    loader: requireAuth,
    element: shell(
      <RequireRole roles={['admin', 'curator', 'marketing']} fallbackPath="/golden">
        <RunReportPage />
      </RequireRole>,
    ),
  },
  { path: '*', element: <Navigate to="/candidates" replace /> },
]);
