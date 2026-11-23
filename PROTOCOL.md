# Can AI Assistants Get SNAP Households to the Right Store?

Protocol v1, 22 November 2026. Tejaswi Suresh, RankSaga Ltd.

## Question

Tens of millions of Americans get SNAP. USDA says SNAP online purchasing now works in all 50 states and DC, but only at retailers authorized for it, only for eligible food, and never for delivery or service fees. When a SNAP household asks an AI assistant where it can order groceries online with an EBT card, does the answer send it somewhere that will actually take the card?

This study measures that, state by state, and repeats each month as a running index.

## Two parts

1. **Answers.** What an AI assistant with live web search tells SNAP shoppers in all 50 states and DC.
2. **Plumbing.** Whether the protocols now used for AI agent checkout (Google's Universal Commerce Protocol, UCP, and OpenAI and Stripe's Agentic Commerce Protocol, ACP) can carry an EBT payment at all. If they cannot, an agent that shops on a person's behalf cannot complete a SNAP order however good its answers are.

## Part 1 design

52 places (the largest city in each state and DC, plus Buffalo for New York State outside NYC) x 12 questions = 624 questions per wave.

| Framing | Prompt (exact text in `study/config.py`) | What it tests |
| --- | --- | --- |
| where | "I get SNAP and want to order groceries online with my EBT card. I live in {place}. Which stores can I use?" | Which stores it names |
| nocar | "I'm on SNAP and don't have a car. I live in {place}. What's the cheapest way to get groceries delivered and pay with my EBT card?" | Stores named, and what it says about fees |
| check x 10 | "Can I pay with my SNAP EBT card for an online grocery order from {retailer}? I live in {place}." | A yes or no with a right answer |

The ten retailers asked about by name are Walmart, Amazon, ALDI, Costco, Whole Foods, Kroger, Safeway, Publix, Sprouts and Gopuff. They were chosen because the right answer depends on where the shopper lives: Publix trades in a handful of southeastern states, ALDI in about 39, Safeway mainly in the West.

Prompts never mention USDA, delivery apps or any store, so the assistant chooses what to say.

**Assistant.** Wave 1 uses Google Gemini through the Gemini API with Grounding with Google Search, which is how the Gemini app answers with live results. The system message carries only the date and the shopper's city. The model version served is logged on every call. Calls go through the paid Gemini API (Tier 1).

## Answer key

The answer key has two layers, because no single public source is complete.

1. **Retailer policy (primary).** For each of the ten panel retailers, its own published SNAP online policy (help or FAQ pages) and the states where it trades under that name: `data/reference/retailer_policies.json`, with a source URL for every entry.
2. **USDA list (secondary).** USDA's Food and Nutrition Service publishes a page per state of retailers accepting SNAP online. Those pages are blocked to automated requests, so the study uses Internet Archive captures from December 2025 to June 2026 (`data/reference/usda_snapshots.txt`, parsed into `usda_snap_online.csv`; 1,536 entries across 52 pages). The pages turned out to be incomplete: Kroger has accepted EBT online at every Kroger Family store since 2023, yet the Texas page does not list it. So USDA's list never overrides the retailer layer. Where the two disagree, that disagreement is reported as a finding of its own.

The New York City page lists only stores added for the city, so NYC is scored against the city and statewide pages together.

## Coding and scoring

Each answer is coded by a separate Gemini call with no search, at temperature 0, into a fixed schema: the stores and delivery apps it names, whether it says each takes EBT online, its yes or no verdict for the check questions, what it says about fees, and whether it tells the shopper to confirm with USDA, the state agency or the store.

| Measure | Definition |
| --- | --- |
| Wrong store | A store the answer says takes EBT online where the retailer's own policy says it does not (or does not trade there) |
| Unverified store | A store neither the retailer table nor the USDA page confirms. A random sample is checked by hand against the store's own website and reported |
| Check accuracy | Share of check questions whose verdict matches the answer key |
| False yes rate | Of the cases where the right answer is no, how often the assistant said yes. This is the costly error: a household plans a week's food around a store that will not take the card |
| False no rate | Of the cases where the right answer is yes, how often it said no |
| Fee error | The answer says or implies SNAP can pay delivery or service fees. USDA rules say it cannot, so this is right or wrong in every state |
| Points to official | The answer tells the shopper to confirm with USDA, the state agency or the retailer |

The two layers below were added on 23 November 2026, after wave 1, when the first scores showed that a state-level key misjudges city-level answers.

**Hand check.** The answer key is set by state, but each question names a city, and a chain that trades in a state may have no store serving that city (Safeway has none in Los Angeles or Las Vegas). So every check question where the assistant disagreed with the key, and every store scored wrong in an open answer, is checked by hand at city level against the retailer's store locator (`data/reference/adjudications.csv`, with a source for each row). Final scores use the hand check; scores against the key alone are reported beside them. Cases that turn on cross-border delivery and cannot be settled without a ZIP code lookup are left out as unclear. **City coverage.** To catch the opposite case, a yes where the chain trades in the state but has no store serving the city, every retailer and city pair the assistant said yes to was checked against the retailer's own store locator, with local news for recent openings and closings (`data/reference/city/<retailer>.csv`, 254 pairs, a source for each). A city counts as served when a store under the retailer's own name (not a sister banner) is within about 20 miles of the city centre; pairs that hinge on cross-border or borderline delivery are left out as unclear. Amazon ships SNAP groceries nationwide, so it serves every city. Final scores use the right answer for the shopper's city: the state key, corrected by the hand check and the city table.

Not scored: a parent chain named where it trades under another banner (for example Kroger in Colorado, where its stores are King Soopers), and delivery apps such as Instacart or DoorDash, which pass orders to stores and are reported separately.

## Part 2 method

A read of the current UCP and ACP specifications for any way to (a) offer or submit an EBT instrument, (b) mark which line items are SNAP-eligible, and (c) split one order between EBT for eligible food and a card for the rest, which every SNAP online order needs. First reading (22 November 2026):

* UCP (main branch, 20 November 2026): only `card` has a normative instrument schema; the Split Payments extension splits a total across instruments by amount and priority, with no notion of item eligibility; no EBT or SNAP terms anywhere in the spec.
* ACP (spec version 2026-04-17): payment method is `card`, with card funding type limited to credit, debit or prepaid; no EBT.

If confirmed, the finding goes to both projects as a proposal for an EBT tender with item-level eligibility, which would also serve HSA and FSA cards.

## Rules

* Questions are asked to an assistant, never to stores. No orders, accounts or contact with retailers.
* All prompts, answers, codes and scores are published with each wave.
* Retailers and assistants are named only on the basis of the published data.

## Outputs

* `data/raw/runs.jsonl`: every prompt and full answer with its search sources.
* `data/derived/codes.jsonl`, `stores.csv`, `checks.csv`: coded answers, one row per store named and per check question.
* `results/summary.md`: headline numbers, by retailer and by state.

Code is MIT licensed; data is CC BY 4.0. USDA pages are US government works in the public domain.
