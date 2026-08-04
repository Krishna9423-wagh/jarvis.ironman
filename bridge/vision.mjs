import { createSdkMcpServer, tool } from '@anthropic-ai/claude-agent-sdk'
import { z } from 'zod'

/**
 * JARVIS's eyes.
 *
 * Everything else in this bridge pushes: a panel appears, a blade opens, the
 * interface retints. This is the one capability that has to ask and wait — the
 * camera is in the browser, the model is here, and a frame has to travel back.
 * So it rides a request/reply channel rather than the one-way stream the rest
 * of the tools use.
 *
 * Worth being deliberate about what this is. It turns on a camera pointed at
 * the user's face and hands the picture to a model. That is a reasonable thing
 * to do when they have just said "look at me", and an unreasonable thing to do
 * because a model got curious mid-answer. Three things keep it honest:
 *
 *   - the browser refuses unless the page is already allowed the camera, so the
 *     operating system's own permission still gates it;
 *   - the indicator is on screen for the whole time the camera is live, and the
 *     hardware light is on with it;
 *   - the persona is told, in as many words, to use it only when asked to look.
 *
 * No frame is stored. It is captured, encoded, handed to the model for the
 * turn, and gone.
 */

const DESCRIPTION = `Look through the camera at whoever is in front of the screen.

Captures one frame and returns it as an image you can actually see and describe.

Use it when the user asks you to look — "what am I holding", "how do I look",
"is anyone behind me", "read this label", "what colour is this". Anything where
the answer is in front of the camera rather than on the machine.

Do NOT use it speculatively. It switches on a camera pointed at their face, and
the indicator and the hardware light both come on. Take a picture because they
asked you to take a picture, not because a picture might be informative.

One frame per question. If you need to see something again after they have
moved or turned it around, take another — do not ask them to hold still while
you reason about a picture you already have.`

/**
 * @param {(kind: string, args: object) => Promise<object>} ask
 *   Sends a request to the browser and resolves with its reply.
 */
export function visionServer(ask) {
  return createSdkMcpServer({
    name: 'jarvis_eyes',
    version: '1.0.0',
    instructions:
      "The camera on the user's machine, pointed at them. Use it when they ask " +
      'you to look at something. It is not a sensor to poll; it is an act.',
    // Behind tool search, "look at me" would find nothing and become an apology.
    alwaysLoad: true,
    tools: [
      tool(
        'look',
        DESCRIPTION,
        {
          reason: z
            .string()
            .optional()
            .catch(undefined)
            .describe(
              'A few words on what you are looking for, shown to the user while ' +
                'the camera is live. They can see the light; tell them why.',
            ),
        },
        async (args) => {
          let reply
          try {
            reply = await ask('capture', { reason: String(args.reason ?? '').slice(0, 80) })
          } catch (err) {
            return {
              isError: true,
              content: [
                {
                  type: 'text',
                  text:
                    `Could not reach the camera: ${err?.message ?? err}. ` +
                    'Tell the user you cannot see and carry on without it.',
                },
              ],
            }
          }

          if (reply?.error) {
            // Worded so the model can pass it on as one plain sentence. A denied
            // camera is a fact about the machine, not a failure to apologise for.
            return {
              isError: true,
              content: [{ type: 'text', text: String(reply.error) }],
            }
          }
          if (typeof reply?.data !== 'string' || !reply.data) {
            return {
              isError: true,
              content: [{ type: 'text', text: 'The camera returned nothing.' }],
            }
          }

          return {
            content: [
              { type: 'text', text: 'One frame from the camera:' },
              {
                type: 'image',
                data: reply.data,
                mimeType: reply.mimeType ?? 'image/jpeg',
              },
            ],
          }
        },
      ),
    ],
  })
}
