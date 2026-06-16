"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re
from collections import Counter

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if token}


def _size_matches(requested_size: str | None, listing_size: str) -> bool:
    if requested_size is None:
        return True

    requested = requested_size.strip().lower()
    candidate = listing_size.strip().lower()

    if not requested:
        return True

    if requested == candidate:
        return True

    normalized_candidate = re.sub(r"\s+", "", candidate)
    normalized_requested = re.sub(r"\s+", "", requested)

    if normalized_requested in normalized_candidate:
        return True

    if re.fullmatch(r"[a-z]+\d+[a-z0-9/\-() ]*", normalized_requested):
        return normalized_requested in normalized_candidate

    pattern = rf"(^|[^a-z0-9]){re.escape(normalized_requested)}([^a-z0-9]|$)"
    return re.search(pattern, normalized_candidate) is not None


def _score_listing(description: str, listing: dict) -> int:
    query_tokens = _tokenize(description)
    if not query_tokens:
        return 0

    searchable_parts = [
        listing.get("title", ""),
        listing.get("description", ""),
        listing.get("category", ""),
        " ".join(listing.get("style_tags", [])),
        " ".join(listing.get("colors", [])),
        listing.get("brand") or "",
        listing.get("platform", ""),
        listing.get("size", ""),
    ]
    searchable_text = " ".join(searchable_parts).lower()
    searchable_tokens = _tokenize(searchable_text)

    score = len(query_tokens & searchable_tokens)

    title_text = listing.get("title", "").lower()
    description_text = listing.get("description", "").lower()
    style_tags_text = " ".join(listing.get("style_tags", [])).lower()
    if description.lower() in title_text:
        score += 4
    elif description.lower() in description_text:
        score += 3

    for phrase, title_bonus, tag_bonus in (("graphic tee", 4, 1), ("band tee", 4, 1), ("baby tee", 1, 1)):
        if phrase in description.lower():
            if phrase in title_text:
                score += title_bonus
            elif phrase in style_tags_text:
                score += tag_bonus

    style_tags = [tag.lower() for tag in listing.get("style_tags", [])]
    score += sum(1 for tag in style_tags if tag in query_tokens)

    category = listing.get("category", "").lower()
    if category in query_tokens:
        score += 1

    return score


def _build_listing_summary(listing: dict) -> str:
    brand = listing.get("brand") or "unbranded"
    return (
        f"{listing.get('title', 'Untitled item')} — ${listing.get('price', 0):.2f}, "
        f"{listing.get('platform', 'unknown platform')}, {listing.get('condition', 'unknown condition')}"
        f" [{brand}]"
    )


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()
    description = description.strip()

    matching_listings: list[tuple[int, dict]] = []
    for listing in listings:
        price = float(listing.get("price", 0))
        if max_price is not None and price > max_price:
            continue

        listing_size = str(listing.get("size", ""))
        if size is not None and not _size_matches(size, listing_size):
            continue

        score = _score_listing(description, listing)
        if score <= 0:
            continue

        matching_listings.append((score, listing))

    matching_listings.sort(
        key=lambda pair: (
            -pair[0],
            float(pair[1].get("price", 0)),
            pair[1].get("title", ""),
        )
    )
    return [listing for _, listing in matching_listings]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    wardrobe_items = wardrobe.get("items") or []
    client = _get_groq_client()

    item_summary = (
        f"Title: {new_item.get('title', 'Unknown item')}\n"
        f"Category: {new_item.get('category', 'unknown')}\n"
        f"Size: {new_item.get('size', 'unknown')}\n"
        f"Colors: {', '.join(new_item.get('colors', [])) or 'none'}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', [])) or 'none'}\n"
        f"Price: ${float(new_item.get('price', 0)):.2f}\n"
        f"Platform: {new_item.get('platform', 'unknown')}"
    )

    if not wardrobe_items:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are FitFindr, a styling assistant. Give concise, practical "
                    "style advice using only the new item. Do not mention that the "
                    "wardrobe is empty; instead suggest what kinds of pieces would "
                    "pair well and describe the overall vibe."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Suggest general styling ideas for this item because the user has no wardrobe items yet.\n\n"
                    f"New item:\n{item_summary}"
                ),
            },
        ]
    else:
        wardrobe_summary = []
        for item in wardrobe_items:
            wardrobe_summary.append(
                f"- {item.get('name', 'Unnamed item')} | {item.get('category', 'unknown')} | "
                f"colors: {', '.join(item.get('colors', [])) or 'none'} | "
                f"style tags: {', '.join(item.get('style_tags', [])) or 'none'} | "
                f"notes: {item.get('notes') or 'none'}"
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are FitFindr, a styling assistant. Suggest one or two complete "
                    "outfits that pair the new item with specific wardrobe pieces. Keep "
                    "the response concise, visual, and realistic. Mention the chosen items "
                    "by name and give a brief styling note for each outfit."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"New item:\n{item_summary}\n\n"
                    "Wardrobe items:\n"
                    + "\n".join(wardrobe_summary)
                ),
            },
        ]

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.7,
        max_tokens=400,
    )
    content = response.choices[0].message.content or ""
    return content.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return "Error: outfit is missing or empty, so a fit card cannot be created yet."

    client = _get_groq_client()
    item_summary = (
        f"Title: {new_item.get('title', 'Unknown item')}\n"
        f"Price: ${float(new_item.get('price', 0)):.2f}\n"
        f"Platform: {new_item.get('platform', 'unknown')}\n"
        f"Condition: {new_item.get('condition', 'unknown')}\n"
        f"Category: {new_item.get('category', 'unknown')}"
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are FitFindr. Write a short, casual, social-media-style fit "
                    "card caption. Keep it natural, specific, and not overly polished. "
                    "Mention the item name, price, and platform once each."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"New item details:\n{item_summary}\n\n"
                    f"Outfit suggestion:\n{outfit}\n\n"
                    "Write a 2-4 sentence caption that sounds like a real OOTD post. "
                    "Keep it concise and add one vivid vibe descriptor."
                ),
            },
        ],
        temperature=0.9,
        max_tokens=220,
    )
    content = response.choices[0].message.content or ""
    return content.strip()
