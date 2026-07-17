import { Box, Button, Grid, Heading, HStack, Stack, Text, Textarea } from '@chakra-ui/react'
import {
  Form,
  redirect,
  useActionData,
  useLoaderData,
  useNavigation,
  useParams,
} from 'react-router-dom'

import {
  type LearningScreen,
  completeExposure,
  completePractice,
  getLearningState,
  request,
  resumeReinforcement,
  startLearning,
  submitAudioRecitation,
  submitTypedRecitation,
} from '../api/client'
import { ApiError } from '../api/errors'

type LearnActionData = {
  error?: string
  screen?: LearningScreen
}

type ShadowPractice = {
  kind: 'shadow_typing' | 'masked_recall'
  canonical_text: string | null
  masked_text: string | null
  level: number
  max_level: number
  mismatch_excerpt: string | null
}

export async function learnLoader({ params }: { params: { psalmNumber?: string } }) {
  return getLearningState(Number(params.psalmNumber))
}

export async function learnAction({
  params,
  request: routeRequest,
}: {
  params: { psalmNumber?: string }
  request: Request
}): Promise<LearnActionData | Response> {
  const psalmNumber = Number(params.psalmNumber)
  const formData = await routeRequest.formData()
  const intent = String(formData.get('intent') ?? '')
  const targetToken = String(formData.get('target_token') ?? '') || undefined
  const text = String(formData.get('text') ?? '')
  const audio = formData.get('audio')

  try {
    if (intent === 'start') return { screen: await startLearning(psalmNumber) }
    if (intent === 'complete-exposure') {
      return { screen: await completeExposure(psalmNumber, { target_token: targetToken }) }
    }
    if (intent === 'complete-practice') {
      return { screen: await completePractice(psalmNumber, { target_token: targetToken }) }
    }
    if (intent === 'submit-shadow-typing') {
      return {
        screen: await request<LearningScreen>(
          `/api/v1/psalms/${psalmNumber}/learning/practice/shadow-typing`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_token: targetToken, text }),
          },
        ),
      }
    }
    if (intent === 'resume-reinforcement') {
      return { screen: await resumeReinforcement(psalmNumber, { target_token: targetToken }) }
    }
    if (intent === 'submit-text') {
      return {
        screen: await submitTypedRecitation(psalmNumber, {
          target_token: targetToken,
          text,
        }),
      }
    }
    if (intent === 'submit-audio' && audio instanceof File) {
      const payload = new FormData()
      payload.set('audio', audio)
      if (targetToken) payload.set('target_token', targetToken)
      return { screen: await submitAudioRecitation(psalmNumber, payload) }
    }
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message }
    throw error
  }

  return redirect(`/learn/${psalmNumber}`)
}

export function LearnPage() {
  const params = useParams()
  const loaderScreen = useLoaderData() as LearningScreen
  const actionData = useActionData() as LearnActionData | undefined
  const navigation = useNavigation()
  const psalmNumber = Number(params.psalmNumber)
  const screen = actionData?.screen ?? loaderScreen
  const activeTarget = screen.active_target
  const activePassage = screen.active_passage
  const assessment = screen.assessment
  const isSubmitting = navigation.state === 'submitting'
  const practice = screen.practice as ShadowPractice | null

  return (
    <Stack gap="6">
      <Stack gap="2">
        <Heading size="lg">Learn Psalm {psalmNumber}</Heading>
        <Text color="fg.muted">Work through exposure, copywork, recall, and recitation.</Text>
      </Stack>

      {actionData?.error ? (
        <Box rounded="lg" borderWidth="1px" borderColor="red.300" bg="red.50" p="4">
          <Text color="red.700">{actionData.error}</Text>
        </Box>
      ) : null}

      <Box rounded="xl" borderWidth="1px" bg="bg.panel" p="6">
        <Stack gap="4">
          <Text fontWeight="semibold">Screen: {screen.screen.replaceAll('_', ' ')}</Text>
          {activeTarget ? <Text color="fg.muted">Current target: {activeTarget.label}</Text> : null}

          {screen.screen === 'exposure' && activePassage ? (
            <Stack gap="4">
              <Text whiteSpace="pre-wrap">{activePassage.canonical_text}</Text>
              <Form method="post">
                <input name="target_token" type="hidden" value={activeTarget?.token ?? ''} />
                <Button colorPalette="purple" loading={isSubmitting} name="intent" type="submit" value="complete-exposure">
                  Continue
                </Button>
              </Form>
            </Stack>
          ) : null}

          {screen.screen === 'practice' && practice?.kind === 'shadow_typing' ? (
            <Form method="post">
              <Stack gap="4">
                <Stack gap="1">
                  <Heading size="md">Shadow typing</Heading>
                  <Text color="fg.muted">Copy the passage while looking at it. This is copywork, not a memory test.</Text>
                </Stack>
                {practice.mismatch_excerpt ? (
                  <Box rounded="md" borderWidth="1px" borderColor="orange.300" bg="orange.50" p="3">
                    <Text color="orange.800">Check near: “{practice.mismatch_excerpt}”</Text>
                  </Box>
                ) : null}
                <Grid gap="4" templateColumns={{ base: '1fr', lg: '1fr 1fr' }}>
                  <Box rounded="lg" borderWidth="1px" p="4">
                    <Text mb="2" fontWeight="semibold">Canonical text</Text>
                    <Text whiteSpace="pre-wrap">{practice.canonical_text}</Text>
                  </Box>
                  <Stack gap="2">
                    <Text fontWeight="semibold">Your copy</Text>
                    <Textarea minH="320px" name="text" placeholder="Type the passage exactly as shown" resize="vertical" required />
                  </Stack>
                </Grid>
                <input name="target_token" type="hidden" value={activeTarget?.token ?? ''} />
                <Button colorPalette="purple" loading={isSubmitting} name="intent" type="submit" value="submit-shadow-typing">
                  Check copywork
                </Button>
              </Stack>
            </Form>
          ) : null}

          {screen.screen === 'practice' && practice?.kind === 'masked_recall' ? (
            <Stack gap="4">
              <Text color="fg.muted">Practice level {practice.level}</Text>
              <Text whiteSpace="pre-wrap">{practice.masked_text}</Text>
              <Form method="post">
                <input name="target_token" type="hidden" value={activeTarget?.token ?? ''} />
                <Button colorPalette="purple" loading={isSubmitting} name="intent" type="submit" value="complete-practice">
                  Complete practice level
                </Button>
              </Form>
            </Stack>
          ) : null}

          {screen.screen === 'ready_for_recitation' ? (
            <Form method="post">
              <Stack gap="4">
                <input name="target_token" type="hidden" value={activeTarget?.token ?? ''} />
                <Textarea minH="220px" name="text" placeholder="Type your recitation here" resize="vertical" />
                <Button colorPalette="purple" loading={isSubmitting} name="intent" type="submit" value="submit-text">
                  Submit typed recitation
                </Button>
              </Stack>
            </Form>
          ) : null}

          {screen.screen === 'ready_for_recitation' ? (
            <Form encType="multipart/form-data" method="post">
              <Stack gap="4">
                <input name="target_token" type="hidden" value={activeTarget?.token ?? ''} />
                <Text color="fg.muted">Or upload recorded audio for spoken assessment.</Text>
                <input accept="audio/*" name="audio" type="file" />
                <Button loading={isSubmitting} name="intent" type="submit" value="submit-audio" variant="outline">
                  Submit spoken recitation
                </Button>
              </Stack>
            </Form>
          ) : null}

          {screen.screen === 'reinforcement' && activePassage ? (
            <Stack gap="4">
              <Text whiteSpace="pre-wrap">{activePassage.canonical_text}</Text>
              <Form method="post">
                <input name="target_token" type="hidden" value={activeTarget?.token ?? ''} />
                <Button colorPalette="purple" loading={isSubmitting} name="intent" type="submit" value="resume-reinforcement">
                  Resume practice
                </Button>
              </Form>
            </Stack>
          ) : null}

          {assessment ? (
            <Box rounded="lg" borderWidth="1px" p="4">
              <Stack gap="2">
                <Text fontWeight="semibold">Latest assessment</Text>
                <HStack gap="4" wrap="wrap">
                  <Text>Result: {assessment.result}</Text>
                  <Text>Accuracy: {assessment.weighted_accuracy.toFixed(3)}</Text>
                  <Text>Remaining passes: {assessment.remaining_successes_required}</Text>
                </HStack>
              </Stack>
            </Box>
          ) : null}

          {['section_completed', 'consolidation_started'].includes(screen.screen) ? (
            <Form method="post">
              <Button colorPalette="purple" loading={isSubmitting} name="intent" type="submit" value="start">
                Continue learning
              </Button>
            </Form>
          ) : null}

          {screen.screen === 'psalm_completed' ? (
            <Text color="green.700">Psalm learned. Review scheduling is now active.</Text>
          ) : null}
        </Stack>
      </Box>
    </Stack>
  )
}
