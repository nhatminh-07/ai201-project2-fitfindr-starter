# FitFindr

FitFindr is a small agent that searches secondhand listings, suggests an outfit from a user wardrobe, and turns the result into a shareable fit-card caption.

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root and add your Groq key:

```text
GROQ_API_KEY=your_key_here
```

Run the CLI test harness:

```bash
python agent.py
```

Run the Gradio app:

```bash
python app.py
```

## Data Sources

- `data/listings.json` contains the mock marketplace inventory.
- `data/wardrobe_schema.json` defines the wardrobe structure and includes example and empty wardrobes.
- `utils/data_loader.py` provides `load_listings()`, `get_example_wardrobe()`, and `get_empty_wardrobe()`.

## Tool Inventory

| Tool | Inputs | Outputs | Purpose |
|---|---|---|---|
| `search_listings` | `description: str`, `size: str | None`, `max_price: float | None` | `list[dict]` of matching listing records from `data/listings.json` | Find the best marketplace item for the user request by filtering and ranking listings. |
| `suggest_outfit` | `new_item: dict`, `wardrobe: dict` | `str` outfit suggestion written by the LLM | Suggest 1–2 ways to style the chosen listing with items from the user's wardrobe. |
| `create_fit_card` | `outfit: str`, `new_item: dict` | `str` fit-card caption written by the LLM, or an error string if the outfit is empty | Turn the outfit idea into a short caption that sounds like a real social post. |

### `search_listings`

This tool reads the marketplace catalog with `load_listings()` and filters by size and maximum price before scoring the remaining items against the description. It returns the matching listing dictionaries sorted from best match to weakest match.

### `suggest_outfit`

This tool sends the selected listing and wardrobe to Groq's `llama-3.3-70b-versatile` model. When the wardrobe is empty, it still returns styling advice instead of crashing, so the agent can keep the interaction moving.

### `create_fit_card`

This tool sends the chosen outfit and item details to the LLM and asks for a short, casual caption. If the outfit string is empty or whitespace only, it returns an error message string instead of raising an exception.

## Planning Loop

The planning loop is linear and stops as soon as a required step fails:

1. Parse the user's request into search filters: description, size, and max price.
2. Call `search_listings` with those filters.
3. If the search returns no results, stop immediately and tell the user what to change.
4. Save the top listing as `selected_item`.
5. Call `suggest_outfit` with the selected listing and the current wardrobe.
6. If the outfit cannot be produced, stop and report the failure.
7. Save the outfit string as `outfit_suggestion`.
8. Call `create_fit_card` with the outfit and selected item.
9. Return the final session state with the listing summary, outfit suggestion, and caption.

This matches the Mermaid diagram in `planning.md`: user request -> parse -> search -> maybe stop -> outfit -> maybe stop -> fit card.

## State Management

FitFindr passes data through a session dictionary so each step can reuse the result of the previous one without recomputing it.

The session tracks:

- `query`: the original user message
- `parsed`: the extracted search filters
- `search_results`: the ranked listings from `search_listings`
- `selected_item`: the top matching listing
- `wardrobe`: the wardrobe passed into the agent
- `outfit_suggestion`: the text returned by `suggest_outfit`
- `fit_card`: the caption returned by `create_fit_card`
- `error`: a message if the interaction stops early

The state is strictly linear. The agent stores the chosen listing before styling it, and it stores the outfit before generating the caption. If a step fails, the agent returns early and does not invent missing values.

## Error Handling

### `search_listings`

Failure mode: no listings match the query.

Agent response: stop immediately and tell the user to adjust the description, size, or max price.

Concrete example from testing: `search_listings("designer ballgown", size="XXS", max_price=5)` returned `[]`, and `run_agent("designer ballgown size XXS under $5", get_example_wardrobe())` returned the error `No listings matched that search. Try changing the description, size, or max price.` with `fit_card` left as `None`.

### `suggest_outfit`

Failure mode: the wardrobe is empty or cannot support a styling suggestion.

Agent response: do not crash. Return a helpful styling response or an explicit error message depending on the caller's guard.

Concrete example from testing: the pytest suite monkeypatched the Groq client and verified that the empty-wardrobe path still returns a string and sends a prompt that says the user has no wardrobe items yet.

### `create_fit_card`

Failure mode: the outfit string is missing or empty.

Agent response: return a descriptive error string instead of calling the model.

Concrete example from testing: `create_fit_card("", {"title": "Graphic Tee"})` returned an error message containing the word `error` rather than raising an exception.

## Spec Reflection

The planning doc helped keep the implementation aligned with the required flow, but I still had to make a few concrete decisions while coding:

- I used a regex-based parser in `agent.py` instead of calling another LLM, because the loop only needs simple filters and the tests are easier to reason about.
- I kept the session dict as the single source of truth so the UI and the CLI can both read the same `selected_item`, `outfit_suggestion`, and `fit_card` values.
- I tuned the listing ranking so the walkthrough query `vintage graphic tee under $30` surfaces the intended graphic tee first rather than a generic top.
- I kept the failure branches strict: no search results means the agent stops before outfit generation, and an empty outfit string means the fit-card step returns an error string.

## AI Usage

I used AI in two specific places while building the project.

1. I gave an AI subagent the Planning Loop, State Management, Error Handling, and Architecture sections from `planning.md`, along with the Mermaid flowchart. It returned a concise pseudocode outline for `run_agent()` and a parsing strategy based on regex. I kept the linear session flow and the early-stop behavior, but I overrode its suggestion to rely on a looser fallback parser and tightened it so the search description no longer included wardrobe-style commentary.

2. I used AI assistance again while refining the agent flow and query parsing. I fed it the session structure from `agent.py` and the tool contracts from `tools.py`, and it highlighted that the top result, outfit, and caption needed to be passed through the session dict rather than recomputed. I kept that state-flow design, but I overrode the first-pass parsing logic and ranking behavior after testing showed that a generic top could outrank the intended graphic tee.

## Running Tests

```bash
pytest tests/
```

The current test suite covers the search success and failure paths, the empty-wardrobe outfit path, and the empty-outfit fit-card guard.
