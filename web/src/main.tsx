import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { RouterProvider } from 'react-router-dom'

import { appRouter } from './app/router'
import { AppProviders } from './app/providers'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppProviders>
      <RouterProvider router={appRouter} />
    </AppProviders>
  </StrictMode>,
)
