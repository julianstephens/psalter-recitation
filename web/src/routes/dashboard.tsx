import { Badge, Box, Grid, Heading, HStack, Stack, Text } from '@chakra-ui/react'
import { Link, useLoaderData, useRouteLoaderData } from 'react-router-dom'

import type {
  InstallationSummary,
  ProgressPayload,
  PsalmListItem,
  ReviewItem,
} from '../api/client'

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
  const { progress, reviews, psalms } = useLoaderData() as {
    progress: ProgressPayload
    reviews: ReviewItem[]
    psalms: PsalmListItem[]
  }
  const activePsalm = psalms.find((item) => item.learning.sections_learned > 0) ?? psalms[0]

  return (
    <Stack gap="6">
      <Box rounded="xl" borderWidth="1px" bg="bg.panel" p="8">
        <Stack gap="3">
          <Heading size="lg">Dashboard</Heading>
          <Text color="fg.muted">
            The dashboard now reads the same installation, progress, and review data that the
            CLI uses.
          </Text>
        </Stack>
      </Box>

      <Grid templateColumns={{ base: '1fr', md: 'repeat(4, 1fr)' }} gap="4">
        <StatCard label="Catalog status" value={installation.catalog_status} />
        <StatCard
          label="Installed translations"
          value={installation.installed_translations.length}
        />
        <StatCard
          label="Default translation"
          value={installation.default_translation_id ?? 'None'}
        />
        <StatCard label="Reviews due" value={progress.summary.reviews_due} />
      </Grid>

      <Grid templateColumns={{ base: '1fr', lg: '1.3fr 1fr' }} gap="4">
        <Box rounded="xl" borderWidth="1px" bg="bg.panel" p="6">
          <Stack gap="4">
            <Heading size="md">Continue learning</Heading>
            {activePsalm ? (
              <Stack gap="2">
                <Text fontWeight="semibold">
                  Psalm {activePsalm.psalm_number} ({activePsalm.translation_id})
                </Text>
                <Text color="fg.muted">
                  Status: {activePsalm.learning.status.replaceAll('_', ' ')}
                </Text>
                <Text color="fg.muted">
                  Sections learned: {activePsalm.learning.sections_learned}/
                  {activePsalm.learning.section_count}
                </Text>
                <Text asChild color="purple.600" fontWeight="medium">
                  <Link to={`/psalms/${activePsalm.psalm_number}`}>Open Psalm details</Link>
                </Text>
              </Stack>
            ) : (
              <Text color="fg.muted">No Psalms available yet.</Text>
            )}
          </Stack>
        </Box>

        <Box rounded="xl" borderWidth="1px" bg="bg.panel" p="6">
          <Stack gap="4">
            <Heading size="md">Due reviews</Heading>
            {reviews.length === 0 ? (
              <Text color="fg.muted">No reviews are due.</Text>
            ) : (
              reviews.slice(0, 5).map((review) => (
                <Box key={review.passage_id}>
                  <HStack gap="2" wrap="wrap">
                    <Text fontWeight="semibold">Psalm {review.psalm_number}</Text>
                    <Badge>{review.translation_id}</Badge>
                  </HStack>
                  <Text color="fg.muted">
                    {review.reason} - {review.due_label}
                  </Text>
                </Box>
              ))
            )}
          </Stack>
        </Box>
      </Grid>
    </Stack>
  )
}
