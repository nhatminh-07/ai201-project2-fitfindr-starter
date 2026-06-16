"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


def _parse_query(query: str) -> dict:
    """Extract description, size, and max_price from a free-form query."""
    cleaned_query = query.strip()
    size = None
    max_price = None

    size_patterns = [
        r"\bsize\s*[:=]?\s*(W\d+(?:\s*L\d+)?|\d+(?:/\d+)?|XXXL|XXL|XL|L|M|S|One Size)\b",
    ]
    for pattern in size_patterns:
        match = re.search(pattern, cleaned_query, flags=re.IGNORECASE)
        if match:
            size = match.group(1)
            break

    price_patterns = [
        r"(?:under|below|less than|max(?:imum)?(?: price)?)\s*\$?(\d+(?:\.\d+)?)",
        r"\$?(\d+(?:\.\d+)?)\s*(?:or less|and under|max)",
        r"\$?(\d+(?:\.\d+)?)\s*(?:to|\-|–)\s*\$?(\d+(?:\.\d+)?)",
    ]
    for pattern in price_patterns:
        match = re.search(pattern, cleaned_query, flags=re.IGNORECASE)
        if not match:
            continue
        if match.lastindex and match.lastindex >= 2 and match.group(2):
            max_price = float(match.group(2))
        else:
            max_price = float(match.group(1))
        break

    description = cleaned_query
    if size:
        description = re.sub(rf"\bsize\s*[:=]?\s*{re.escape(size)}\b", "", description, flags=re.IGNORECASE)
        description = re.sub(rf"\b{re.escape(size)}\b", "", description, flags=re.IGNORECASE)
    if max_price is not None:
        price_string = str(int(max_price)) if max_price.is_integer() else str(max_price)
        description = re.sub(
            rf"(?:under|below|less than|max(?:imum)?(?: price)?)\s*\$?{re.escape(price_string)}",
            "",
            description,
            flags=re.IGNORECASE,
        )
        description = re.sub(
            rf"\$?{re.escape(price_string)}\s*(?:or less|and under|max)",
            "",
            description,
            flags=re.IGNORECASE,
        )
        description = re.sub(
            rf"\$?{re.escape(price_string)}\s*(?:to|\-|–)\s*\$?\d+(?:\.\d+)?",
            "",
            description,
            flags=re.IGNORECASE,
        )

    description = re.sub(
        r"(?i)^\s*(i(?:'m)?\s+looking for|looking for|find me|show me|search for|need|want)\s+",
        "",
        description,
    )
    description = re.split(
        r"\b(i mostly wear|what'?s out there|how would i style|what would you style|how should i style)\b",
        description,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    description = re.sub(r"\s*,\s*", " ", description)
    description = re.sub(r"\s+", " ", description).strip(" ,")
    description = re.sub(r"^(?:a|an|the)\s+", "", description, flags=re.IGNORECASE)
    description = description.rstrip(" .?!")

    if not description:
        description = cleaned_query

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    session = _new_session(query, wardrobe)
    parsed = _parse_query(query)
    session["parsed"] = parsed

    search_results = search_listings(
        parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )
    session["search_results"] = search_results

    if not search_results:
        session["error"] = (
            "No listings matched that search. Try changing the description, "
            "size, or max price."
        )
        return session

    selected_item = search_results[0]
    session["selected_item"] = selected_item

    outfit_suggestion = suggest_outfit(selected_item, wardrobe)
    session["outfit_suggestion"] = outfit_suggestion

    if not outfit_suggestion or not outfit_suggestion.strip():
        session["error"] = "Could not generate an outfit suggestion from the available wardrobe."
        return session

    fit_card = create_fit_card(outfit_suggestion, selected_item)
    session["fit_card"] = fit_card

    if not fit_card or not fit_card.strip():
        session["error"] = "Could not generate a fit card from the outfit suggestion."
        session["fit_card"] = None
        return session

    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe
    import os

    if os.environ.get("GROQ_API_KEY"):
        print("=== Happy path: graphic tee ===\n")
        session = run_agent(
            query="looking for a vintage graphic tee under $30",
            wardrobe=get_example_wardrobe(),
        )
        if session["error"]:
            print(f"Error: {session['error']}")
        else:
            print(f"Found: {session['selected_item']['title']}")
            print(f"\nOutfit: {session['outfit_suggestion']}")
            print(f"\nFit card: {session['fit_card']}")
    else:
        print("=== Happy path skipped: GROQ_API_KEY is not set ===\n")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
