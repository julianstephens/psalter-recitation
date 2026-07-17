import { Badge, Box, Heading, Stack, Text } from '@chakra-ui/react'
import { useLoaderData } from 'react-router-dom'

import type { SettingsPayload } from '../api/client'

export function SettingsPage() {
  const settings = useLoaderData() as SettingsPayload

  return (
    <Stack gap="6">
      <Stack gap="2">
        <Heading size="lg">Settings</Heading>
        <Text color="fg.muted">Current installation and application settings exposed to the web UI.</Text>
      </Stack>

      <Box rounded="xl" borderWidth="1px" bg="bg.panel" p="6">
        <Stack gap="3">
          <Text fontWeight="semibold">Installation</Text>
          <Text color="fg.muted">Catalog status: {settings.catalog_status}</Text>
          <Text color="fg.muted">Scripture provider: {settings.scripture_provider}</Text>
          <Text color="fg.muted">
            Default translation: {settings.default_translation_id ?? 'Not configured'}
          </Text>
          <Text color="fg.muted">Log level: {settings.log_level}</Text>
          {settings.last_error ? <Badge colorPalette="red">{settings.last_error}</Badge> : null}
        </Stack>
      </Box>

      <Box rounded="xl" borderWidth="1px" bg="bg.panel" p="6">
        <Stack gap="3">
          <Text fontWeight="semibold">Installed translations</Text>
          {settings.installed_translations.map((item) => (
            <Text key={item.translation_id} color="fg.muted">
              {item.translation_id} - {item.psalm_count} Psalms
              {item.is_default ? ' (default)' : ''}
            </Text>
          ))}
        </Stack>
      </Box>
    </Stack>
  )
}
