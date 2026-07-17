import { Badge, Box, Grid, Heading, Stack, Text } from '@chakra-ui/react'
import { Navigate, useRouteLoaderData } from 'react-router-dom'

import type { InstallationSummary } from '../api/client'

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Box rounded="xl" borderWidth="1px" bg="bg.panel" p="6">
      <Text color="fg.muted" fontSize="sm" textTransform="uppercase" letterSpacing="0.08em">
        {label}
      </Text>
      <Text mt="2" fontSize="2xl" fontWeight="bold">
        {value}
      </Text>
    </Box>
  )
}

export function DashboardPage() {
  const installation = useRouteLoaderData('root') as InstallationSummary

  if (!installation.is_ready) {
    return <Navigate to="/setup" replace />
  }

  return (
    <Stack gap="6">
      <Box rounded="xl" borderWidth="1px" bg="bg.panel" p="8">
        <Stack gap="3">
          <Heading size="lg">Dashboard</Heading>
          <Text color="fg.muted">
            This shell is already consuming the new API boundary. Psalm catalog, progress,
            and learning screens are the next UI slices to land.
          </Text>
        </Stack>
      </Box>

      <Grid templateColumns={{ base: '1fr', md: 'repeat(3, 1fr)' }} gap="4">
        <StatCard label="Catalog status" value={installation.catalog_status} />
        <StatCard
          label="Installed translations"
          value={installation.installed_translations.length}
        />
        <StatCard
          label="Default translation"
          value={installation.default_translation_id ?? 'None'}
        />
      </Grid>

      <Box rounded="xl" borderWidth="1px" bg="bg.panel" p="6">
        <Stack gap="3">
          <Text fontWeight="semibold">Installed translations</Text>
          {installation.installed_translations.map((item) => (
            <Box key={item.translation_id}>
              <Text>
                {item.translation_id} — {item.psalm_count} Psalms{' '}
                {item.is_default ? <Badge colorPalette="green">default</Badge> : null}
              </Text>
            </Box>
          ))}
        </Stack>
      </Box>
    </Stack>
  )
}
