import { Badge, Box, Container, Flex, HStack, Stack, Text } from '@chakra-ui/react'
import { Link, Outlet, useRouteLoaderData } from 'react-router-dom'

import type { InstallationSummary } from '../api/client'

function NavLink({ to, label }: { to: string; label: string }) {
  return (
    <Text asChild color="fg.muted" fontWeight="medium">
      <Link to={to}>{label}</Link>
    </Text>
  )
}

export function AppShell() {
  const installation = useRouteLoaderData('root') as InstallationSummary

  return (
    <Box minH="100vh" bg="bg.subtle">
      <Container maxW="6xl" py="6">
        <Stack gap="6">
          <Flex
            direction={{ base: 'column', md: 'row' }}
            gap="4"
            align={{ base: 'flex-start', md: 'center' }}
            justify="space-between"
          >
            <Stack gap="1">
              <Text fontSize="sm" color="fg.muted" textTransform="uppercase" letterSpacing="0.12em">
                Psalter Recitation
              </Text>
              <HStack gap="3" wrap="wrap">
                <Text fontSize="2xl" fontWeight="bold">
                  Web UI
                </Text>
                <Badge colorPalette={installation.is_ready ? 'green' : 'orange'}>
                  {installation.catalog_status}
                </Badge>
              </HStack>
              <Text color="fg.muted">
                Default translation: {installation.default_translation_id ?? 'Not initialized'}
              </Text>
            </Stack>

            <HStack gap="4" wrap="wrap">
              <NavLink to="/setup" label="Setup" />
              <NavLink to="/dashboard" label="Dashboard" />
            </HStack>
          </Flex>

          <Outlet />
        </Stack>
      </Container>
    </Box>
  )
}
