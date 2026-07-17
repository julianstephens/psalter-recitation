import {
  Badge,
  Box,
  Button,
  Heading,
  HStack,
  Stack,
  Text,
} from '@chakra-ui/react'
import {
  Form,
  redirect,
  useActionData,
  useLoaderData,
  useNavigation,
  useRouteLoaderData,
} from 'react-router-dom'

import {
  type InstallationSummary,
  type TranslationSummary,
  getTranslations,
  initializeInstallation,
  repairInstallation,
  resumeInstallation,
} from '../api/client'
import { ApiError } from '../api/errors'

type SetupLoaderData = {
  translations: TranslationSummary[]
}

type SetupActionData = {
  error: string
}

export async function setupLoader(): Promise<SetupLoaderData> {
  return {
    translations: await getTranslations(),
  }
}

export async function setupAction({ request }: { request: Request }) {
  const formData = await request.formData()
  const intent = String(formData.get('intent') ?? '')
  const translationId = String(formData.get('translation_id') ?? '').trim()

  try {
    if (intent === 'initialize') {
      await initializeInstallation({ translation_id: translationId })
      return redirect('/dashboard')
    }

    if (intent === 'resume') {
      await resumeInstallation({
        translation_id: translationId || undefined,
      })
      return redirect('/dashboard')
    }

    if (intent === 'repair') {
      await repairInstallation({
        translation_id: translationId || undefined,
      })
      return redirect('/dashboard')
    }
  } catch (error) {
    if (error instanceof ApiError) {
      return { error: error.message }
    }
    throw error
  }

  return { error: 'Unsupported setup action.' }
}

export function SetupPage() {
  const installation = useRouteLoaderData('root') as InstallationSummary
  const { translations } = useLoaderData() as SetupLoaderData
  const actionData = useActionData() as SetupActionData | undefined
  const navigation = useNavigation()
  const submitting = navigation.state === 'submitting'

  if (installation.is_ready) {
    return (
      <Box rounded="xl" borderWidth="1px" bg="bg.panel" p="8">
        <Stack gap="6">
          <Stack gap="2">
            <Heading size="lg">Psalter is ready</Heading>
            <Text color="fg.muted">
              The default translation is {installation.default_translation_id}. Continue to the
              dashboard to begin building the rest of the web workflow.
            </Text>
          </Stack>
          <Button asChild alignSelf="flex-start" colorPalette="purple">
            <a href="/dashboard">Open dashboard</a>
          </Button>
        </Stack>
      </Box>
    )
  }

  return (
    <Box rounded="xl" borderWidth="1px" bg="bg.panel" p="8">
      <Stack gap="6">
        <Stack gap="2">
          <Heading size="lg">Set up Psalter</Heading>
          <Text color="fg.muted">
            Choose a translation and initialize the catalog through the web adapter. Resume and
            repair actions reuse the same installation service as the CLI.
          </Text>
        </Stack>

        <HStack gap="3" wrap="wrap">
          <Badge colorPalette="orange">{installation.catalog_status}</Badge>
          {installation.last_error ? <Badge colorPalette="red">error present</Badge> : null}
        </HStack>

        <Text color="fg.muted">Scripture provider: {installation.scripture_provider}</Text>
        <Text color="fg.muted">
          Installed translations: {installation.installed_translations.length}
        </Text>

        {actionData?.error ? (
          <Box rounded="lg" borderWidth="1px" borderColor="red.300" bg="red.50" p="4">
            <Text color="red.700">{actionData.error}</Text>
          </Box>
        ) : null}

        <Form method="post">
          <Stack gap="4" align="flex-start">
            <Stack gap="2" w="full" maxW="sm">
              <Text fontWeight="semibold">Translation</Text>
              <select
                name="translation_id"
                defaultValue={translations[0]?.id ?? ''}
                style={{
                  border: '1px solid var(--chakra-colors-border)',
                  borderRadius: '0.375rem',
                  background: 'var(--chakra-colors-bg)',
                  padding: '0.5rem 0.75rem',
                }}
              >
                {translations.map((translation) => (
                  <option key={translation.id} value={translation.id}>
                    {translation.id} - {translation.name}
                  </option>
                ))}
              </select>
            </Stack>

            <HStack gap="3" wrap="wrap">
              <Button
                colorPalette="purple"
                loading={submitting}
                name="intent"
                type="submit"
                value="initialize"
              >
                Initialize catalog
              </Button>
              <Button
                loading={submitting}
                name="intent"
                type="submit"
                value="resume"
                variant="outline"
              >
                Resume installation
              </Button>
              <Button
                colorPalette="orange"
                loading={submitting}
                name="intent"
                type="submit"
                value="repair"
                variant="outline"
              >
                Repair catalog
              </Button>
            </HStack>
          </Stack>
        </Form>

        {installation.installed_translations.length > 0 ? (
          <Stack gap="2">
            <Text fontWeight="semibold">Installed translations</Text>
            {installation.installed_translations.map((item) => (
              <Text key={item.translation_id} color="fg.muted">
                {item.translation_id} - {item.psalm_count} Psalms
                {item.is_default ? ' (default)' : ''}
              </Text>
            ))}
          </Stack>
        ) : null}
      </Stack>
    </Box>
  )
}
