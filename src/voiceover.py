"""
Renders narration text to speech using edge-tts (free, no API key required,
uses Microsoft's neural voices) AND captures the exact time each word is
spoken, so captions can be synced word-by-word.

Swap VOICE for any voice from `edge-tts --list-voices` if you want a
different tone.
"""
import asyncio
import re
import edge_tts

VOICE = "en-US-ChristopherNeural"  # try en-US-AriaNeural, en-GB-RyanNeural, etc.
RATE = "+10%"  # a touch faster than default keeps Shorts feeling snappy

_TICKS_PER_SECOND = 10_000_000  # edge-tts reports offsets in 100-nanosecond units


async def _synthesize(text: str, output_path: str, voice: str):
    communicate = edge_tts.Communicate(text, voice, rate=RATE, boundary="WordBoundary")
    words = []
    with open(output_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / _TICKS_PER_SECOND
                end = start + chunk["duration"] / _TICKS_PER_SECOND
                words.append({"word": chunk["text"], "start": start, "end": end})
    return words


def estimate_word_timings(text: str, total_duration: float):
    """
    Fallback when the TTS service doesn't return word timings: spread the
    words across the audio in proportion to their length.
    """
    tokens = re.findall(r"[\w'’-]+", text)
    if not tokens or total_duration <= 0:
        return []
    weights = [len(t) + 2 for t in tokens]
    scale = total_duration / sum(weights)
    words, t = [], 0.0
    for token, w in zip(tokens, weights):
        dur = w * scale
        words.append({"word": token, "start": t, "end": t + dur * 0.9})
        t += dur
    return words


def generate_voiceover(text: str, output_path: str, voice: str = VOICE):
    """
    Writes the narration audio to output_path and returns a list of
    {"word", "start", "end"} dicts (seconds). The list may be empty if the
    TTS service didn't send timings; the assembler estimates them then.
    """
    return asyncio.run(_synthesize(text, output_path, voice))


if __name__ == "__main__":
    w = generate_voiceover(
        "This is a test of the automated voiceover system.",
        "test_narration.mp3",
    )
    print("Saved test_narration.mp3")
    for item in w:
        print(item)
