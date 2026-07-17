import { Box, Container, Heading, Text } from '@chakra-ui/react'
import { isRouteErrorResponse, useRouteError } from 'react-router-dom'

import { getErrorMessage } from '../api/errors'

export function RouteErrorBoundary() {
  const error = useRouteError()
  const message = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : getErrorMessage(error)

  return (
    <Container maxW="4xl" py="24">
      <Box rounded="xl" borderWidth="1px" p="8">
        <Heading size="lg">Unable to load Psalter</Heading>
        <Text mt="4" color="fg.muted">
          {message}
        </Text>
      </Box>
    </Container>
  )
}
