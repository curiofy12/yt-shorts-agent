"""
Turns a topic into a ready-to-produce short: hook, narration script,
visual keyword cues (for stock footage search), title, description, tags.
"""
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ANTHROPIC_API_KEY, TARGET_DURATION_SECONDS
import anthropic

SYSTEM_PROMPT = f"""You write scripts for faceless YouTube Shorts channels.
Output ONLY valid JSON, no markdown fences, no preamble. Schema:

{{
  "hook": "first 3 seconds, must stop the scroll",
  "narration": "full narration script, {TARGET_DURATION_SECONDS} seconds when read aloud at natural pace (~130 wpm), written as plain spoken sentences",
  "caption_segments": ["short phrase 1", "short phrase 2", "..."],
  "visual_keywords": ["3-6 concrete search terms for stock footage matching the narration, e.g. 'ocean waves aerial', 'brain scan closeup'"],
  "title": "under 100 chars, curiosity-driven, no clickbait falsehoods",
  "description": "2-3 sentences plus 3-5 relevant hashtags",
  "tags": ["8-12 relevant tags"]
}}

Rules:
- narration must be factually accurate; do not invent statistics or fabricate sources
- caption_segments should break the narration into short on-screen phrases (roughly one per sentence or clause), in order
- keep language simple, punchy, second person where natural
- no copyrighted lyrics, no real named private individuals
"""


def generate_script(topic: str) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Topic for today's short: {topic}"}
        ],
    )

    raw = message.content[0].text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Script generator returned invalid JSON: {e}\nRaw: {raw}")


if __name__ == "__main__":
    result = generate_script("a mind-bending space fact")
    print(json.dumps(result, indent=2))
