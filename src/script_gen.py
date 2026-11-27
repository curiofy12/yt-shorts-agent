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

def _stock_prompt():
    from globe_data import icon_names
    icons = ", ".join(icon_names())
    return f"""You write scripts for faceless YouTube Shorts channels. The video cuts between stock footage clips, one per beat, with punchy motion graphics: 3D icons pop onto the screen and striking numbers fly in huge.
Output ONLY valid JSON, no markdown fences, no preamble. Schema:

{{
{BASE_SCHEMA},
  "beats": [
    {{
      "text": "the exact part of the narration spoken during this beat (one short sentence or clause)",
      "search": "concrete stock-footage search term for what's on screen, e.g. 'ocean waves aerial', 'brain scan closeup'",
      "icon": "a 3D icon that pops on screen to illustrate this beat, one of: {icons} — or empty string if nothing fits",
      "big_number": "a striking number from this beat shown huge on screen, max 8 characters with short units (K, M, B, %, km), e.g. '4,000 M', '90%', 'x3' — or empty string",
      "whoosh": "true only if this beat opens with a big jump that deserves a whoosh: a sudden change of place, era or scale, or a dramatic reveal ('But then...', 'Meanwhile, 4,000 metres down...'); false for ordinary cuts"
    }}
  ]
}}

{BASE_RULES}
- 8-10 beats. Joined together in order, the beats' "text" fields must equal the narration exactly, word for word
- use an icon on only 2-3 beats per video, for the most important or visual moments, never on two beats in a row
- use big_number only when that beat actually states a number, and keep it consistent with the narration
- whoosh: at most 2-3 per video and never on the first beat; most cuts should be plain
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


def _globe_prompt():
    from globe_data import REGIONS, icon_names
    regions = ", ".join(REGIONS)
    icons = ", ".join(icon_names())
    return f"""You write scripts for a faceless YouTube Shorts series in the style of "Every second on Earth...": a satellite world map where the camera flies between regions while 3D icons pop onto the map and huge numbers fly in. Each beat is one striking, true statistic.
Output ONLY valid JSON, no markdown fences, no preamble. Schema:

{{
{BASE_SCHEMA},
  "beats": [
    {{
      "text": "the exact part of the narration spoken during this beat (usually one short sentence)",
      "view": "where the camera goes, one of: {regions}",
      "icon": "icon to scatter on the map, one of: {icons} (or empty string)",
      "count": "how many copies of the icon pop onto the map, 1-30 (more = more dramatic)",
      "big_number": "the stat shown huge on screen, max 8 characters, use short units (K, M, B, T, %, km), e.g. '4.3', '$15,000', 'x3', '20 M', or empty string",
      "effect": "ripples (for earthquakes, impacts, signals) or none"
    }}
  ]
}}

{BASE_RULES}
- 8-11 beats. Joined together in order, the beats' "text" fields must equal the narration exactly, word for word
- open with a hook like "Every second on Earth..." or "In the next 30 seconds..." and then rapid-fire beats
- ONLY use well-established, widely published figures (UN, WHO, NASA, USGS, World Bank, IEA and similar), rounded the way those sources round them. If you are not confident a figure is right, choose a different statistic. Say "about" or "roughly" where the figure is an estimate
- keep the time unit consistent with the hook (per second, per minute, per day) and do the conversion correctly
- choose a "view" that matches where the fact happens; use "world" for global facts and "space" only for facts about Earth's motion or space
- never name brands, companies or real people; describe things generically ("a soda", "the world's richest people")
- the big_number must match what the narration says in that beat"""


FACT_CHECK_PROMPT = """You are a meticulous fact-checker for a YouTube Shorts channel. You'll get a JSON script of statistic "beats". For each beat, check the figure against widely published sources (UN, WHO, NASA, USGS, World Bank, IEA, etc.) as of your knowledge.
- If a figure is right (allowing normal rounding), keep the beat unchanged.
- If it's wrong or a per-second/per-day conversion is off, correct the number in BOTH "text" and "big_number".
- If it can't be verified with confidence, rewrite the beat with a different, well-established statistic on the same theme, or remove the beat.
- Keep "hook", "hook_title", "title" and the opening consistent with any changes.
Work through each figure step by step first (show your arithmetic). Then, at the very end, output the full corrected script in exactly the same schema inside a ```json code block, with a top-level "fact_check_notes" string summarising what you changed (or "no changes"). Nothing after the code block."""


def _parse_json(text):
    """Parses the JSON in a reply, even if reasoning text comes before it."""
    import re
    blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if blocks:
        raw = blocks[-1]
    else:
        start, end = text.find("{"), text.rfind("}")
        raw = text[start:end + 1] if start != -1 and end > start else text
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Script generator returned invalid JSON: {e}\nRaw: {raw}")


def _fact_check(client, script):
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=FACT_CHECK_PROMPT,
        messages=[{"role": "user", "content": json.dumps(script, ensure_ascii=False)}],
    )
    checked = _parse_json(msg.content[0].text)
    print(f"[script] fact check: {checked.get('fact_check_notes', 'no notes')}")
    return checked


def generate_script(topic: str, avoid_titles=None, style: str = "stock") -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    if style == "illustrated":
        system = ILLUSTRATED_PROMPT
    elif style == "globe":
        system = _globe_prompt()
    else:
        system = _stock_prompt()

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

    script = _parse_json(message.content[0].text)

    if style == "globe":
        from globe_data import REGIONS, icon_names
        script = _fact_check(client, script)
        icons = set(icon_names())
        beats = []
        for b in script.get("beats", []):
            if not b.get("text"):
                continue
            b["view"] = b.get("view") if b.get("view") in REGIONS else "world"
            b["icon"] = b.get("icon") if b.get("icon") in icons else ""
            try:
                b["count"] = max(0, min(int(b.get("count") or 0), 30))
            except (TypeError, ValueError):
                b["count"] = 8
            num = str(b.get("big_number") or "").strip()
            while len(num) > 9 and " " in num:
                num = num.rsplit(" ", 1)[0]  # "20 M tonnes" -> "20 M"
            b["big_number"] = num[:9]
            beats.append(b)
        if len(beats) < 3:
            raise ValueError("Script generator returned too few globe beats.")
        script["beats"] = beats
        script["narration"] = " ".join(b["text"].strip() for b in beats)

    if style == "stock":
        from globe_data import icon_names
        icons = set(icon_names())
        beats = []
        for b in script.get("beats", []):
            if not b.get("text"):
                continue
            b["search"] = (b.get("search") or "").strip() or "nature landscape aerial"
            b["icon"] = b.get("icon") if b.get("icon") in icons else ""
            num = str(b.get("big_number") or "").strip()
            while len(num) > 9 and " " in num:
                num = num.rsplit(" ", 1)[0]
            b["big_number"] = num[:9]
            b["whoosh"] = str(b.get("whoosh")).lower() == "true" and len(beats) > 0
            beats.append(b)
        if len(beats) < 3:
            raise ValueError("Script generator returned too few stock beats.")
        # Keep whooshes special: at most 3 per video
        n = 0
        for b in beats:
            if b["whoosh"]:
                n += 1
                b["whoosh"] = n <= 3
        # Icons are accents: at most 3 per video, never on back-to-back beats
        shown, last = 0, -2
        for i, b in enumerate(beats):
            if b["icon"]:
                if shown >= 3 or i - last < 2:
                    b["icon"] = ""
                else:
                    shown += 1
                    last = i
        script["beats"] = beats
        script["narration"] = " ".join(b["text"].strip() for b in beats)
        script["visual_keywords"] = [b["search"] for b in beats]

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
