# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
The tool searches the mock listings dataset for the best matches to the user's description, size, and price.
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): description of the listing  
- `size` (str): size of the clothes, with starting = S, M, L, XL, or other custom numbers
- `max_price` (float): a number that represent a maximum price that it could pay

**What it returns:**
- Three best matches value that it could use for a match like this
- I would think they will return a value that it could be returned: the description have to match with the description of the listing by cosine similarity rules. The sizes could be returned as all that matches the sizes --> there are special cases to not match all exact strings but get close enough search engine results
<!-- Describe the return value — what fields does a result contain? -->

**What happens if it fails or returns nothing:**
- Do not hallucinate this, you should return that the search failed to find anything.
- Add empty item in a wardrobe
<!-- What should the agent do if no listings match? -->

---

### Tool 2: suggest_outfit

**What it does:**

<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): a new item, returned from tool 1 as the best choice of purchase
- `wardrobe` (dict): the original wardrobe that the user places

**What it returns:**
A specific ID of a outfit, embedded in a JSON code, matches the color of the string. Again, outfit is divided as ID, name (identification only), category, colors, style tags, 
<!-- Describe the return value -->

**What happens if it fails or returns nothing:**
- If the wardrobe is empty, you should inform that nothing could be selected. You could suggest or search listing for other or prompt the user to search any other preferences.
- The search return nothing close (the cosine similarity is low): you could return: I cannot find anything close to match any of your preferences, you should choose the next ones.
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (...): ...

**What it returns:**
<!-- Describe the return value -->

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | |
| suggest_outfit | Wardrobe is empty | |
| create_fit_card | Outfit input is missing or incomplete | |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

**Milestone 4 — Planning loop and state management:**

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

FitFindr should first search the marketplace listings for the best matching item using the user's size and price constraints. If a listing is found, it should use that listing as the `new_item` and combine it with the user's wardrobe `items` to suggest an outfit, then turn the final outfit into a short fit-card caption. If no listings match, it should explain what to change in the search and stop without calling `suggest_outfit`.

**Step 1:**
Call `search_listings(description="vintage graphic tee", size="M", max_price=30.0)`. This searches `data/listings.json` for marketplace items that match the request and returns the best few listings, already filtered by the tool's rules.
<!-- What does the agent do first? Which tool is called? With what input? -->

**Step 2:**
Take the top matching listing, for example `Faded Band Tee — $22, Depop, Good condition.` Use that listing as `new_item` and pass it together with the wardrobe object from `data/wardrobe_schema.json` into `suggest_outfit(new_item=..., wardrobe=...)`. If `search_listings` returns no results, stop here and tell the user to try a different size, price, or description.
<!-- What happens next? What was returned from step 1? What tool is called now? -->

**Step 3:**
Use the suggested outfit to call `create_fit_card(outfit=..., new_item=...)`. This generates the short, social-media-style caption that describes the full look in the user's voice.
<!-- Continue until the full interaction is complete -->

**Final output to user:**
A fit card caption, such as: "thrifted this faded band tee off depop for $22 and honestly it was made for my wide-legs 🖤 full look in my stories"
<!-- What does the user actually see at the end? -->
