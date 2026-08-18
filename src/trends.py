"""
Finds today's candidate topic.

Note: pytrends' realtime trending-search endpoint has been unreliable
(Google has changed/removed it), so this pulls from a large curated
topic pool instead of live trends. This is intentional -- a broken
"live trends" call that silently falls back to a tiny topic list is
worse than a large, deliberately varied static pool.

If CHANNEL_NICHE is set in .env, topics are angled toward that niche so
the channel stays on-brand.
"""
import random
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CHANNEL_NICHE

FALLBACK_TOPICS = [
    "a surprising psychology fact about human memory",
    "an unsolved mystery from history",
    "a mind-bending space fact",
    "a strange law of physics explained simply",
    "an animal ability that sounds fake but is real",
    "a historical event most people misunderstand",
    "a fact about the human body that sounds impossible",
    "a technology prediction from the past that came true",
    "an ocean mystery scientists can't fully explain",
    "a cognitive bias that affects daily decisions",
    "a lost civilization and what happened to it",
    "an everyday object with a surprising origin story",
    "a scientific discovery that was initially ridiculed",
    "a survival ability humans still have but rarely use",
    "a mathematical pattern that shows up in nature",
    "a famous historical figure's little-known side career",
    "a food that used to be considered poisonous or dangerous",
    "an ancient invention more advanced than expected",
    "a language fact that changes how you think about words",
    "a weather phenomenon that seems impossible but is real",
    "a myth about the human brain that's actually false",
    "an animal migration that defies explanation",
    "a historical coincidence that seems too strange to be true",
    "a psychological experiment with a surprising result",
    "a geographic feature that shouldn't exist but does",
    "a common misconception about space that's actually wrong",
    "an invention that was created completely by accident",
    "a hidden pattern in how cities or societies grow",
    "a sense or ability certain animals have that humans don't",
    "a historical event that almost changed the world but didn't",
    "a fact about sleep that most people don't know",
    "an economic concept explained through a strange real example",
    "a natural phenomenon that inspired a major invention",
    "a decoding of an ancient mystery that took centuries to solve",
    "a fact about the internet or technology's hidden infrastructure",
    "a strange law that's still on the books somewhere",
    "an unexpected connection between two unrelated fields of science",
    "a record-breaking natural event and what caused it",
    "a historical figure who was more radical than people realize",
    "a common phrase or idiom with a surprising true origin",
    "an animal behavior that looks like it shouldn't be possible",
    "a scientific theory that was proven right decades later",
    "a place on Earth that feels like it shouldn't exist",
    "a psychological trick advertisers or media use on you",
    "an ancient technology we still don't fully understand",
]


def get_trending_topics(max_results=10):
    """
    Returns a shuffled slice of the curated topic pool.
    (Live Google Trends pulling was removed after proving consistently
    unreliable in production -- see module docstring.)
    """
    pool = FALLBACK_TOPICS.copy()
    random.shuffle(pool)
    return pool[:max_results]


def pick_topic(recent_topics=None):
    """
    Picks one topic for today, avoiding repeats from recent_topics
    (a list of strings from posts_log.json). Picks randomly among the
    non-recent candidates rather than always taking the first match, so
    variety doesn't collapse to the same handful of topics over time.
    """
    recent_topics = recent_topics or []
    candidates = get_trending_topics(max_results=len(FALLBACK_TOPICS))

    if CHANNEL_NICHE:
        candidates = [f"{t} (angle this through: {CHANNEL_NICHE})" for t in candidates]

    available = [t for t in candidates if t not in recent_topics]

    if available:
        return random.choice(available)

    # Every topic in the pool has been used recently (pool exhausted) --
    # just pick randomly rather than deterministically repeating #1.
    return random.choice(candidates) if candidates else random.choice(FALLBACK_TOPICS)


if __name__ == "__main__":
    print(pick_topic())
