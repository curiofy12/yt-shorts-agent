"""
Builds an animated caption track (.ass subtitle file) that ffmpeg burns
into the video. Three layers:

1. Word-by-word captions: short groups of 1-3 words pop onto the screen
   in sync with the narration, and the word being spoken right now is
   highlighted. This is the caption style most top Shorts channels use.
2. Hook title card: a bold headline at the top for the first few seconds,
   so viewers know instantly what the video is about.
3. Progress bar: a thin bar across the top that fills as the video plays,
   which nudges people to watch to the end.

Positions keep clear of the areas YouTube covers with its own buttons
(bottom ~25% of the screen and the right edge).
"""

# ---- Look & feel (edit these to restyle) ----------------------------------
CAPTION_FONT = "Anton"          # bundled in assets/fonts
CAPTION_SIZE = 136
CAPTION_Y = 1180                # vertical center of captions (screen is 1920 tall)
WORDS_PER_GROUP = 3
HIGHLIGHT_COLOR = "&H0033D6FF&"   # ASS colors are &HAABBGGRR -> warm yellow
TEXT_COLOR = "&H00FFFFFF&"        # white

HOOK_SECONDS = 2.8
HOOK_SIZE = 108
HOOK_Y = 330
HOOK_BOX_COLOR = "&H0033D6FF&"    # yellow box
HOOK_TEXT_COLOR = "&H00101010&"   # near-black text

BAR_HEIGHT = 14
BAR_COLOR = "&H0033D6FF&"

LABEL_SIZE = 74
LABEL_Y = 900                   # place/date labels sit above the captions
LABEL_SECONDS = 2.6
# ---------------------------------------------------------------------------

W, H = 1080, 1920


def _ts(seconds: float) -> str:
    """Seconds -> ASS timestamp (h:mm:ss.cc)."""
    seconds = max(0.0, seconds)
    cs = int(round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _clean(word: str) -> str:
    """Uppercase and strip characters that have special meaning in ASS."""
    return word.replace("\\", "").replace("{", "").replace("}", "").upper()


def _group_words(words):
    """
    Split the word list into short on-screen groups. A new group starts
    after WORDS_PER_GROUP words, or when the narrator pauses (comma/period).
    """
    groups, current = [], []
    for i, w in enumerate(words):
        current.append(w)
        next_start = words[i + 1]["start"] if i + 1 < len(words) else None
        pause = next_start is not None and next_start - w["end"] > 0.22
        if len(current) >= WORDS_PER_GROUP or pause or next_start is None:
            groups.append(current)
            current = []
    return groups


def _caption_events(words):
    events = []
    groups = _group_words(words)
    for gi, group in enumerate(groups):
        group_end = group[-1]["end"] + 0.12
        if gi + 1 < len(groups):
            nxt = groups[gi + 1][0]["start"]
            # Close small gaps so captions don't flicker off between groups
            group_end = nxt if nxt - group_end < 0.4 else min(group_end, nxt)

        for wi, active in enumerate(group):
            start = active["start"]
            end = group[wi + 1]["start"] if wi + 1 < len(group) else group_end
            if end <= start:
                continue

            parts = []
            for wj, w in enumerate(group):
                text = _clean(w["word"])
                if wj == wi:
                    parts.append(f"{{\\c{HIGHLIGHT_COLOR}}}{text}{{\\c{TEXT_COLOR}}}")
                else:
                    parts.append(text)

            # The group "pops" in (scales up from 70%) only when it first appears
            pop = "\\fscx70\\fscy70\\t(0,90,\\fscx100\\fscy100)" if wi == 0 else ""
            tags = f"{{\\an5\\pos({W // 2},{CAPTION_Y}){pop}}}"
            events.append(
                f"Dialogue: 1,{_ts(start)},{_ts(end)},Caption,,0,0,0,,{tags}{' '.join(parts)}"
            )
    return events


def _hook_event(hook_title: str, duration: float):
    if not hook_title:
        return []
    end = min(HOOK_SECONDS, duration)
    tags = (
        f"{{\\an8\\pos({W // 2},{HOOK_Y})"
        "\\fscx60\\fscy60\\t(0,140,\\fscx104\\fscy104)\\t(140,220,\\fscx100\\fscy100)"
        "\\fad(0,250)}"
    )
    return [f"Dialogue: 2,{_ts(0)},{_ts(end)},Hook,,0,0,0,,{tags}{_clean(hook_title)}"]


def _progress_bar_event(duration: float):
    ms = int(duration * 1000)
    shape = f"m 0 0 l {W} 0 {W} {BAR_HEIGHT} 0 {BAR_HEIGHT}"
    tags = (
        f"{{\\an7\\pos(0,0)\\clip(0,0,0,{BAR_HEIGHT})"
        f"\\t(0,{ms},\\clip(0,0,{W},{BAR_HEIGHT}))\\p1}}"
    )
    return [f"Dialogue: 0,{_ts(0)},{_ts(duration)},Bar,,0,0,0,,{tags}{shape}"]


def _label_events(labels, duration):
    """labels: list of (start_seconds, text) for place/date tags like 'CHICAGO, 1930'."""
    events = []
    for start, text in labels or []:
        if not text or start >= duration:
            continue
        end = min(start + LABEL_SECONDS, duration)
        tags = f"{{\\an5\\pos({W // 2},{LABEL_Y})\\fad(200,250)}}"
        events.append(f"Dialogue: 1,{_ts(start)},{_ts(end)},Label,,0,0,0,,{tags}{_clean(text)}")
    return events


def build_ass(words, hook_title: str, duration: float, output_path: str, labels=None):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{CAPTION_FONT},{CAPTION_SIZE},{TEXT_COLOR},{TEXT_COLOR},&H00000000&,&H80000000&,0,0,0,0,100,100,1,0,1,8,5,5,80,130,0,1
Style: Hook,{CAPTION_FONT},{HOOK_SIZE},{HOOK_TEXT_COLOR},{HOOK_TEXT_COLOR},{HOOK_BOX_COLOR},{HOOK_BOX_COLOR},0,0,0,0,100,100,1,0,3,22,0,8,110,110,0,1
Style: Label,{CAPTION_FONT},{LABEL_SIZE},{TEXT_COLOR},{TEXT_COLOR},&H00000000&,&H80000000&,0,0,0,0,100,100,3,0,1,6,3,5,80,80,0,1
Style: Bar,Arial,20,{BAR_COLOR},{BAR_COLOR},&H00000000&,&H00000000&,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = (
        _progress_bar_event(duration)
        + _hook_event(hook_title, duration)
        + _label_events(labels, duration)
        + _caption_events(words)
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")
    return output_path
