import { Badge, Box, Button, Heading, HStack, Stack, Text } from '@chakra-ui/react'
import { Link, Navigate, useRouteLoaderData } from 'react-router-dom'

import type { InstallationSummary } from '../api/client'

export function SetupPage() {
  const installation = useRouteLoaderData('root') as InstallationSummary

  if (installation.is_ready) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <Box rounded="xl" borderWidth="1px" bg="bg.panel" p="8">
      <Stack gap="6">
        <Stack gap="2">
          <Heading size="lg">Set up Psalter</Heading>
          <Text color="fg.muted">
            The router shell is now connected to the Python API. Translation selection,
            initialization actions, and install-progress polling are the next screens to land.
          </Text>
        </Stack>

        <HStack gap="3" wrap="wrap">
          <Badge colorPalette="orange">{installation.catalog_status}</Badge>
          {installation.last_error ? <Badge colorPalette="red">error present</Badge> : null}
        </HStack>

        <Text color="fg.muted">
          Installed translations: {installation.installed_translations.length}
        </Text>

        <Button asChild alignSelf="flex-start" colorPalette="purple">
          <Link to="/dashboard">Continue to placeholder dashboard</Link>
        </Button>
      </Stack>
    </Box>
  )
}
