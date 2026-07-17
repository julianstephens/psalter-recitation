import { createBrowserRouter, Navigate } from 'react-router-dom'

import { getInstallation } from '../api/client'
import { DashboardPage } from '../routes/dashboard'
import { SetupPage } from '../routes/setup'
import { RouteErrorBoundary } from './error-boundary'
import { AppShell } from './shell'

function RootRedirect() {
  return <Navigate to="/setup" replace />
}

export const appRouter = createBrowserRouter([
  {
    id: 'root',
    path: '/',
    loader: getInstallation,
    Component: AppShell,
    errorElement: <RouteErrorBoundary />,
    children: [
      {
        index: true,
        Component: RootRedirect,
      },
      {
        path: 'setup',
        Component: SetupPage,
      },
      {
        path: 'dashboard',
        Component: DashboardPage,
      },
    ],
  },
])
