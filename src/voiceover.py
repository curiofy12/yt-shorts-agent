"""
Renders narration text to speech using edge-tts (free, no API key required,
uses Microsoft's neural voices). Swap VOICE for any voice from
`edge-tts --list-voices` if you want a different tone.
"""
import asyncio
import edge_tts

VOICE = "en-US-ChristopherNeural"  # try en-US-AriaNeural, en-GB-RyanNeural, etc.


async def _synthesize(text: str, output_path: str, voice: str = VOICE):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def generate_voiceover(text: str, output_path: str, voice: str = VOICE):
    asyncio.run(_synthesize(text, output_path, voice))
    return output_path


if __name__ == "__main__":
    generate_voiceover(
        "This is a test of the automated voiceover system.",
        "test_narration.mp3",
    )
    print("Saved test_narration.mp3")
