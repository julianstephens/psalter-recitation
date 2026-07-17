import { Box, Grid, Heading, Stack, Text } from '@chakra-ui/react'
import { useLoaderData } from 'react-router-dom'

import type { ProgressPayload } from '../api/client'

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

export function ProgressPage() {
  const progress = useLoaderData() as ProgressPayload

  return (
    <Stack gap="6">
      <Stack gap="2">
        <Heading size="lg">Progress</Heading>
        <Text color="fg.muted">Aggregate memorization and review progress across the Psalter.</Text>
      </Stack>

      <Grid templateColumns={{ base: '1fr', md: 'repeat(3, 1fr)' }} gap="4">
        <StatCard label="Total passages" value={progress.summary.total_passages} />
        <StatCard label="Learned passages" value={progress.summary.learned_passages} />
        <StatCard label="Reviews due" value={progress.summary.reviews_due} />
        <StatCard label="Exposure" value={progress.summary.exposure_passages} />
        <StatCard label="Practice" value={progress.summary.practice_passages} />
        <StatCard label="Ready" value={progress.summary.ready_passages} />
      </Grid>

      <Box rounded="xl" borderWidth="1px" bg="bg.panel" p="6">
        <Stack gap="3">
          <Heading size="md">Psalm progress</Heading>
          {progress.psalms.map((psalm) => (
            <Text key={psalm.psalm_id} color="fg.muted">
              Psalm {psalm.psalm_number} ({psalm.translation_id}) - {psalm.sections_learned}/
              {psalm.section_count} sections learned
            </Text>
          ))}
        </Stack>
      </Box>
    </Stack>
  )
}
