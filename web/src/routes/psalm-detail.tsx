import { Badge, Box, Button, Grid, Heading, Stack, Text } from '@chakra-ui/react'
import { Link, useLoaderData } from 'react-router-dom'

import type { PsalmDetail } from '../api/client'

export function PsalmDetailPage() {
  const { psalm } = useLoaderData() as { psalm: PsalmDetail }

  return (
    <Stack gap="6">
      <Stack gap="2">
        <Heading size="lg">
          Psalm {psalm.psalm_number} ({psalm.translation_id})
        </Heading>
        <Text color="fg.muted">
          {psalm.learning.sections_learned}/{psalm.learning.section_count} sections learned
        </Text>
      </Stack>

      <Grid templateColumns={{ base: '1fr', lg: '320px 1fr' }} gap="4">
        <Box rounded="xl" borderWidth="1px" bg="bg.panel" p="6">
          <Stack gap="3">
            <Heading size="md">Status</Heading>
            <Badge>{psalm.learning.status.replaceAll('_', ' ')}</Badge>
            <Text color="fg.muted">Verse count: {psalm.verse_count}</Text>
            <Text color="fg.muted">Reviews due: {psalm.learning.reviews_due}</Text>
            <Text color="fg.muted">
              Current section: {psalm.learning.current_section_label ?? 'None'}
            </Text>
            <Button asChild alignSelf="flex-start" colorPalette="purple">
              <Link to={`/learn/${psalm.psalm_number}`}>Start or resume learning</Link>
            </Button>
          </Stack>
        </Box>

        <Box rounded="xl" borderWidth="1px" bg="bg.panel" p="6">
          <Stack gap="4">
            <Heading size="md">Canonical text</Heading>
            {psalm.verses.map((verse) => (
              <Text key={verse.verse_number} lineHeight="1.8">
                <Text as="span" fontWeight="bold">
                  {verse.verse_number}
                </Text>{' '}
                {verse.canonical_text}
              </Text>
            ))}
          </Stack>
        </Box>
      </Grid>
    </Stack>
  )
}
