import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'

import { AppProviders } from '../app/providers'
import { SetupPage } from './setup'

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    Form: ({ children }: { children: React.ReactNode }) => <form>{children}</form>,
    useActionData: () => undefined,
    useLoaderData: () => ({
      translations: [
        {
          id: 'BSB',
          name: 'Berean Standard Bible',
          language: 'en',
          supports_psalms: true,
        },
        {
          id: 'KJV',
          name: 'King James Version',
          language: 'en',
          supports_psalms: true,
        },
      ],
    }),
    useNavigation: () => ({ state: 'idle' }),
    useRouteLoaderData: () => ({
      catalog_status: 'not_started',
      scripture_provider: 'mock',
      default_translation_id: null,
      default_translation_name: null,
      installed_translations: [],
      is_ready: false,
      last_error: null,
    }),
  }
})

describe('SetupPage', () => {
  it('renders the installation form and translations from loader data', async () => {
    render(
      <AppProviders>
        <SetupPage />
      </AppProviders>,
    )

    expect(await screen.findByRole('heading', { name: 'Set up Psalter' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Initialize catalog' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Resume installation' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Repair catalog' })).toBeInTheDocument()
    expect(screen.getByDisplayValue('BSB - Berean Standard Bible')).toBeInTheDocument()
  })
})
