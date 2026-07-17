import { createBrowserRouter, Navigate, redirect, useRouteLoaderData } from 'react-router-dom'

import {
  getInstallation,
  getProgress,
  getPsalm,
  getPsalms,
  getReviews,
  getSettings,
} from '../api/client'
import { DashboardPage } from '../routes/dashboard'
import { learnAction, learnLoader, LearnPage } from '../routes/learn'
import { ProgressPage } from '../routes/progress'
import { PsalmDetailPage } from '../routes/psalm-detail'
import { PsalmsPage } from '../routes/psalms'
import { ReviewsPage } from '../routes/reviews'
import { SettingsPage } from '../routes/settings'
import { setupAction, setupLoader, SetupPage } from '../routes/setup'
import { RouteErrorBoundary } from './error-boundary'
import { AppShell } from './shell'

function RootRedirect() {
  const installation = useRouteLoaderData('root') as Awaited<ReturnType<typeof getInstallation>>
  return <Navigate to={installation.is_ready ? '/dashboard' : '/setup'} replace />
}

async function dashboardLoader() {
  const installation = await getInstallation()
  if (!installation.is_ready) {
    throw redirect('/setup')
  }
  const [progress, reviews, psalms] = await Promise.all([
    getProgress(),
    getReviews(),
    getPsalms(),
  ])
  return { progress, reviews, psalms }
}

async function psalmsLoader() {
  return { psalms: await getPsalms() }
}

async function psalmDetailLoader({ params }: { params: { psalmNumber?: string } }) {
  return {
    psalm: await getPsalm(Number(params.psalmNumber)),
  }
}

async function progressLoader() {
  return getProgress()
}

async function reviewsLoader() {
  return { reviews: await getReviews() }
}

async function settingsLoader() {
  return getSettings()
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
        loader: setupLoader,
        action: setupAction,
        Component: SetupPage,
      },
      {
        path: 'dashboard',
        loader: dashboardLoader,
        Component: DashboardPage,
      },
      {
        path: 'psalms',
        loader: psalmsLoader,
        Component: PsalmsPage,
      },
      {
        path: 'psalms/:psalmNumber',
        loader: psalmDetailLoader,
        Component: PsalmDetailPage,
      },
      {
        path: 'learn/:psalmNumber',
        loader: learnLoader,
        action: learnAction,
        Component: LearnPage,
      },
      {
        path: 'reviews',
        loader: reviewsLoader,
        Component: ReviewsPage,
      },
      {
        path: 'progress',
        loader: progressLoader,
        Component: ProgressPage,
      },
      {
        path: 'settings',
        loader: settingsLoader,
        Component: SettingsPage,
      },
    ],
  },
])
