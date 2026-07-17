import { Badge, Box, Grid, Heading, Stack, Text } from '@chakra-ui/react'
import { Link, useLoaderData } from 'react-router-dom'

import type { PsalmListItem } from '../api/client'

export function PsalmsPage() {
  const { psalms } = useLoaderData() as { psalms: PsalmListItem[] }

  return (
    <Stack gap="6">
      <Stack gap="2">
        <Heading size="lg">Psalms</Heading>
        <Text color="fg.muted">Browse imported Psalms and their current learning status.</Text>
      </Stack>

      <Grid templateColumns={{ base: '1fr', lg: 'repeat(2, 1fr)' }} gap="4">
        {psalms.map((psalm) => (
          <Box key={psalm.id} rounded="xl" borderWidth="1px" bg="bg.panel" p="6">
            <Stack gap="3">
              <Stack gap="1">
                <Text fontWeight="bold">
                  Psalm {psalm.psalm_number} ({psalm.translation_id})
                </Text>
                <Text color="fg.muted">
                  {psalm.learning.sections_learned}/{psalm.learning.section_count} sections learned
                </Text>
              </Stack>

              <Stack direction="row" gap="2" flexWrap="wrap">
                <Badge>{psalm.learning.status.replaceAll('_', ' ')}</Badge>
                <Badge colorPalette={psalm.learning.reviews_due > 0 ? 'orange' : 'green'}>
                  {psalm.learning.reviews_due} reviews due
                </Badge>
              </Stack>

              <Text asChild color="purple.600" fontWeight="medium">
                <Link to={`/psalms/${psalm.psalm_number}`}>Open details</Link>
              </Text>
            </Stack>
          </Box>
        ))}
      </Grid>
    </Stack>
  )
}
