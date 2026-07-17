import { Badge, Box, Button, Heading, Stack, Text } from '@chakra-ui/react'
import { Link, useLoaderData } from 'react-router-dom'

import type { ReviewItem } from '../api/client'

export function ReviewsPage() {
  const { reviews } = useLoaderData() as { reviews: ReviewItem[] }

  return (
    <Stack gap="6">
      <Stack gap="2">
        <Heading size="lg">Reviews</Heading>
        <Text color="fg.muted">Due review work, grouped at the Psalm level.</Text>
      </Stack>

      {reviews.length === 0 ? (
        <Box rounded="xl" borderWidth="1px" bg="bg.panel" p="6">
          <Text color="fg.muted">No reviews are due.</Text>
        </Box>
      ) : (
        reviews.map((review) => (
          <Box key={review.passage_id} rounded="xl" borderWidth="1px" bg="bg.panel" p="6">
            <Stack gap="2">
              <Text fontWeight="bold">Psalm {review.psalm_number}</Text>
              <Stack direction="row" gap="2" flexWrap="wrap">
                <Badge>{review.translation_id}</Badge>
                <Badge colorPalette="orange">{review.reason}</Badge>
              </Stack>
              <Text color="fg.muted">Due label: {review.due_label}</Text>
              <Text color="fg.muted">
                Next review: {review.next_review_at ?? 'Ready now'}
              </Text>
              <Button asChild alignSelf="flex-start" colorPalette="purple" size="sm">
                <Link to={`/learn/${review.psalm_number}`}>Review Psalm</Link>
              </Button>
            </Stack>
          </Box>
        ))
      )}
    </Stack>
  )
}
