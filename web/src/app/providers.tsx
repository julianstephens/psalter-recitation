import type { PropsWithChildren } from 'react'

import { ChakraProvider, defaultSystem } from '@chakra-ui/react'

export function AppProviders({ children }: PropsWithChildren) {
  return <ChakraProvider value={defaultSystem}>{children}</ChakraProvider>
}
