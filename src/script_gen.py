"""
Turns a topic into a ready-to-produce short: hook, narration script,
visuals (stock footage search terms, or illustrated scenes), title,
description, tags.
"""
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ANTHROPIC_API_KEY, TARGET_DURATION_SECONDS
import anthropic

# Measured: the narrator speaks about 2.45 words per second at +10% speed
TARGET_WORDS = int(TARGET_DURATION_SECONDS * 2.45)
MAX_SCENES = 10

BASE_SCHEMA = f"""  "hook": "first 3 seconds, must stop the scroll",
  "hook_title": "2-5 word on-screen headline shown at the top for the first 3 seconds, e.g. 'A RIVER UNDER THE OCEAN' — punchy, no punctuation except ? or !",
  "narration": "full narration script, {TARGET_WORDS - 10} to {TARGET_WORDS} words total (HARD LIMIT — about {TARGET_DURATION_SECONDS} seconds read aloud), written as plain spoken sentences",
  "title": "under 100 chars, curiosity-driven, no clickbait falsehoods",
  "description": "2-3 sentences plus 3-5 relevant hashtags",
  "tags": ["8-12 relevant tags"],
  "comment_question": "a short question posted as the first comment to get viewers talking, under 90 characters, at most one emoji, never 'like and subscribe', e.g. 'Would you swim in it? 🌊'\""""

BASE_RULES = """Rules:
- narration must be factually accurate; do not invent statistics or fabricate sources
- keep language simple, punchy, second person where natural
- every sentence must earn its place: no filler, no "let's dive in", no outro asking to like or subscribe
- LOOP ENDING: the final sentence should flow naturally back into the opening line, so a viewer whose video replays from the start hears one continuous thought (e.g. ending "...and that's why" when the video opens "Scientists still can't explain...")
- no copyrighted lyrics, no real named private individuals"""

STOCK_PROMPT = f"""You write scripts for faceless YouTube Shorts channels.
Output ONLY valid JSON, no markdown fences, no preamble. Schema:

{{
{BASE_SCHEMA},
  "visual_keywords": ["8-10 concrete stock-footage search terms, one per beat of the narration and in the same order, e.g. 'ocean waves aerial', 'brain scan closeup'"]
}}

{BASE_RULES}
"""

ILLUSTRATED_PROMPT = f"""You write scripts for a faceless YouTube Shorts channel whose videos are a sequence of flat 2D cartoon illustrations (simple vector characters with big round heads, moody colors), each shown with a slow camera move.
Output ONLY valid JSON, no markdown fences, no preamble. Schema:

{{
{BASE_SCHEMA},
  "scenes": [
    {{
      "text": "the exact part of the narration spoken during this scene",
      "image_prompt": "what to draw: one concrete, visual moment — setting, time of day, characters and what they're doing, key objects. 1-2 sentences.",
      "label": "optional short on-screen place/date label like 'CHICAGO, 1930' or 'PACIFIC OCEAN, 4,000 M DOWN' — only when it adds context, else empty string",
      "particles": "one of: snow, rain, dust, embers, bubbles, stars, none"
    }}
  ]
}}

{BASE_RULES}
- 8-10 scenes (never more than 10), so a new image appears every 3-4 seconds. Joined together in order, the scenes' "text" fields must equal the narration exactly, word for word
- image prompts must be drawable: describe what is SEEN, never ask for text, signs with words, maps with labels, or logos
- one single shot per image: never split screens, side-by-side panels, before/after comparisons, diagrams or cross-sections
- keep recurring characters visually consistent: describe them the same way in every scene they appear in (e.g. "a tall man in a grey trench coat and fedora")
- vary the shots: mix wide establishing shots, medium shots and close-ups of a key object
- labels: use at most 3 per video, mostly on the first scene and when the place or era changes
"""


def generate_script(topic: str, avoid_titles=None, style: str = "stock") -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    system = ILLUSTRATED_PROMPT if style == "illustrated" else STOCK_PROMPT

    prompt = f"Topic for today's short: {topic}"
    if avoid_titles:
        listed = "\n".join(f"- {t}" for t in avoid_titles)
        prompt += (
            "\n\nThis channel has already made these videos on this topic. "
            "Pick a clearly different specific fact or story — not the same "
            f"subject reworded:\n{listed}"
        )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        script = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Script generator returned invalid JSON: {e}\nRaw: {raw}")

    if style == "illustrated":
        scenes = [s for s in script.get("scenes", []) if s.get("image_prompt")]
        if len(scenes) < 3:
            raise ValueError("Script generator returned too few illustrated scenes.")
        # Cloudflare's free tier allows ~40 images a day; cap scenes so two
        # illustrated videos a day always fit. Extra scenes merge into the last.
        if len(scenes) > MAX_SCENES:
            extra = " ".join(s.get("text", "") for s in scenes[MAX_SCENES:])
            scenes = scenes[:MAX_SCENES]
            scenes[-1]["text"] = (scenes[-1].get("text", "") + " " + extra).strip()
        script["scenes"] = scenes
        # The scene texts are what's spoken, so they ARE the narration
        script["narration"] = " ".join(s.get("text", "").strip() for s in scenes).strip() or script["narration"]
    return script


if __name__ == "__main__":
    result = generate_script("a mind-bending space fact")
    print(json.dumps(result, indent=2))
