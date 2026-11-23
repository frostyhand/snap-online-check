# Can AI Assistants Get SNAP Households to the Right Store?

Wave 1 findings, 23 November 2026. Tejaswi Suresh, RankSaga Ltd.

## Summary

An AI assistant with live web search usually gets SNAP households to a store that will take their EBT card online, but when it fails it fails in one way: it says yes to a chain that has no store serving the shopper's city, usually because the chain trades somewhere else in the state.

I asked Google Gemini 624 questions a SNAP shopper might ask, from the largest city in every state and DC, on 22 and 23 November 2026, and scored every answer against each retailer's own policy and store locator.

- **The rules are right.** All 104 open answers said SNAP cannot pay delivery or service fees. None said it could.
- **Named stores are mostly right.** Asked "can I use my EBT card online at X?", it was right 97.9% of the time (423 questions). It never wrongly said no.
- **Every wrong yes sent the shopper to a chain that does not serve their city.** In all 7, no store of that chain serves the city. In 5 the chain trades elsewhere in the state (Safeway in Anchorage, Kroger in Chicago and St. Louis, Whole Foods in Cheyenne, ALDI in Burlington). In 2 it has no stores in the state at all (Sprouts in Portland, and Whole Foods in Burlington, where Gemini described a store that does not exist).
- **Open answers carry the same error.** 12 of 104 answers (11.5%) named at least one store that cannot serve the shopper. That is 13 of 803 stores named.
- **It almost never says to check.** Only 3 of 104 open answers told the shopper to confirm with USDA, the state SNAP agency or the store.

Two side findings. USDA's own state lists leave out retailers that do take EBT online there (17 retailer and state pairs, still missing on the live pages on 23 November 2026). And neither of the protocols now used for AI agent checkout can carry an EBT payment, so an agent that shops for a SNAP household cannot finish the order at all.

## What I did

I asked 12 questions from each of 52 places: the largest city in each state and DC, plus Buffalo for New York State outside New York City. That is 624 questions.

| Framing | Question asked | Per place |
| --- | --- | --- |
| Where | "I get SNAP and want to order groceries online with my EBT card. I live in {city}. Which stores can I use?" | 1 |
| No car | "I'm on SNAP and don't have a car. I live in {city}. What's the cheapest way to get groceries delivered and pay with my EBT card?" | 1 |
| Check | "Can I pay with my SNAP EBT card for an online grocery order from {retailer}? I live in {city}." | 10 |

The ten retailers in the check questions are Walmart, Amazon, ALDI, Costco, Whole Foods, Kroger, Safeway, Publix, Sprouts and Gopuff. I chose them because the right answer depends on where the shopper lives. No question mentions USDA, a delivery app or a store list, so the assistant decides what to say.

The assistant was Gemini 3.8 Flash through the Gemini API with Grounding with Google Search, the same live search the Gemini app uses. The system message held only the date and the shopper's city. A separate Gemini call with no search, at temperature 0, coded each answer into a fixed form: the stores it names, whether it says each takes EBT online, its yes or no verdict, what it says about fees, and whether it tells the shopper to confirm somewhere official.

## How I scored the answers

No single public source says which stores take EBT online for a given city, so I built the answer key in three layers. Each layer has a source for every entry.

1. **Retailer policy, by state** (`data/reference/retailer_policies.json`). Each of the ten retailers' own SNAP online pages, plus the states where it trades under its own name. Example: Costco takes EBT only through Same-Day delivery (fulfilled by Instacart), never on Costco.com.
2. **Hand check of every disagreement** (`data/reference/adjudications.csv`). Each of the 27 cases where Gemini disagreed with the state key, checked against store locators and local news.
3. **City coverage** (`data/reference/city/*.csv`). Every retailer and city pair Gemini said yes to (254 pairs), checked against the retailer's store locator. A city counts as served when a store under the chain's own name, not a sister banner, is within about 20 miles of the city centre. Amazon ships SNAP groceries nationwide, so it serves every city.

The layers matter. Against the state key alone, Gemini scored 94.4% on the named-retailer questions. The hand check raised that to 99.1%, because 17 of its apparent errors were right for the city: it said no to Safeway in Los Angeles and Las Vegas because neither city has one. The city check then lowered it to 97.9%, because it found 5 wrong yes answers the state key had marked correct.

Cases that turn on delivery across a state line or a borderline distance (Sprouts into DC from Arlington, Whole Foods into Wilmington from Pennsylvania, Kroger delivery in Birmingham) are left out as unclear: 5 questions. Gopuff is reported but left out of the headline, because its state list could only come from USDA. USDA's "Stores Accepting SNAP Online" pages are used only as a second reference, because they turned out to be incomplete.

## Findings

### The rules: right every time

USDA rules say SNAP pays only for eligible food, never for delivery fees, service fees or tips. All 104 open answers said so, and none said otherwise. 89 of them also said a backup card is needed for the rest of the order (by a text search of the answers).

### Named retailers: 97.9% right, never a wrong no

Of 423 scored check questions, Gemini was right on 414, gave a wrong yes on 7 and hedged with no bottom line on 2. Questions where the retailer trades only under a sister banner (Kroger as King Soopers in Colorado, say) are not scored.

| Retailer | Scored | Right | Wrong yes | Hedged | Unclear, left out |
| --- | --- | --- | --- | --- | --- |
| Amazon | 52 | 52 | 0 | 0 | 0 |
| Walmart | 52 | 52 | 0 | 0 | 0 |
| Publix | 51 | 51 | 0 | 0 | 0 |
| ALDI | 52 | 51 | 1 | 0 | 0 |
| Sprouts | 50 | 49 | 1 | 0 | 2 |
| Whole Foods | 51 | 49 | 2 | 0 | 1 |
| Costco | 51 | 49 | 0 | 2 | 1 |
| Safeway | 33 | 32 | 1 | 0 | 0 |
| Kroger | 31 | 29 | 2 | 0 | 1 |
| Gopuff (not in headline) | 52 | 44 | 8 | 0 | 0 |

It was most reliable on the chains that serve nearly everywhere (Amazon, Walmart) and on Publix, whose footprint is small and well known. It also got Costco's unusual rule right: all 52 Costco answers pointed the shopper to Costco Same-Day or Instacart, where EBT works.

### The seven wrong yes answers

| City | Retailer | What Gemini said | Nearest store |
| --- | --- | --- | --- |
| Anchorage, AK | Safeway | Yes | Seward, about 125 road miles; Anchorage stores are branded Carrs |
| Chicago, IL | Kroger | Yes | Bourbonnais, about 55 miles; Chicago stores are branded Mariano's |
| St. Louis, MO | Kroger | Yes | Troy MO or Nashville IL, about 50 miles |
| Cheyenne, WY | Whole Foods | Yes | Fort Collins CO, about 45 miles |
| Burlington, VT | ALDI | Yes | Rutland, about 67 miles |
| Burlington, VT | Whole Foods | Yes, citing a South Burlington store | None in Vermont; the store it described does not exist |
| Portland, OR | Sprouts | Yes | Seattle area; Sprouts has no Oregon stores |

### Open answers: 1 in 9 names a store that cannot serve the shopper

In the 104 open answers, Gemini named 803 stores as places that take EBT online. 13 of them (1.7%) cannot serve the shopper, and 12 answers (11.5%) contain at least one. Sprouts accounts for 10 of the 13: it was suggested in Portland, Little Rock, Jackson, Boise, Wichita, St. Louis, New Orleans, Columbia SC and Richmond, none of which has a Sprouts nearby. The rest are ALDI in Burlington (twice) and Safeway in Boise. Another 33 stores could not be confirmed from my sources and are not scored.

Delivery apps came up 173 times, mostly Instacart. They are not scored, because an app is only as good as the stores it has in that city, but they are a large part of how these answers tell shoppers to order.

### Telling shoppers to check: 3 of 104

Only 3 open answers told the shopper to confirm with USDA's list, the state SNAP agency or the store. Every open answer gave a list of stores; almost none said that list might be wrong for their address.

## The pattern: state or program, not city

Gemini can reason about the shopper's city; it just does not always do it. In 17 answers it got the city right where a state-level answer would have been wrong. It told a shopper in Los Angeles that there are no Safeway stores there and to use Vons or Albertsons instead. It told a shopper in New Orleans that Kroger accepts EBT online but has no stores near the city.

In the 7 failures it answered at the level of the chain's program instead: the retailer takes SNAP online, so the answer is yes. That reasoning is right for Amazon, which ships nationwide, and close to right for Walmart. It breaks for regional chains whose stores cluster in one part of a state, such as Safeway in northern Idaho, Kroger in downstate Illinois or Sprouts in the Kansas City area.

The cost of this error falls on the shopper. A household that plans a week's food around a store that cannot deliver to it finds out only at checkout, after building a cart. A one-line note to check the address on the store's own site would catch it. 101 of 104 open answers gave no such pointer to the store, USDA or the state agency.

## Side finding: USDA's state lists leave stores out

USDA publishes a "Stores Accepting SNAP Online" page for each state. Those pages leave out a panel retailer that, by its own published policy, takes EBT online in that state in 17 cases. I found the gaps in archived copies from December 2025 to June 2026, and all 17 are still there on the live pages, which I read from a US connection on 23 November 2026 (`data/reference/usda_live/`).

| Retailer | States where USDA's page does not list it |
| --- | --- |
| Kroger | Arkansas (lists a banner only), Louisiana, Michigan, Mississippi, Texas, Virginia, West Virginia |
| ALDI | Louisiana, Maine, Nevada |
| Sprouts | New York (state and city pages), Wyoming |
| Whole Foods | Illinois, Montana |
| Publix | Kentucky |
| Walmart | District of Columbia |

Some gaps may be timing: ALDI's first Maine store opened in March 2026, and an archived page can predate an opening. Others cannot be: Kroger has taken EBT online at every Kroger Family store since 2023, and Michigan and Texas are among its largest states. USDA's list is the official reference, so a household that checks it can be told no where the answer is yes.

The pages now sit at fna.usda.gov under the name Food and Nutrition Administration. Between the archived and live copies, 16 state pages lost entries (24 in all), while none of the 17 gaps was filled.

## Plumbing: agent checkout cannot carry EBT yet

Answers are half the problem. AI agents are starting to place orders for people through two checkout protocols: Google's Universal Commerce Protocol (UCP) and OpenAI and Stripe's Agentic Commerce Protocol (ACP). I read both specifications on 22 and 23 November 2026, and neither can carry a SNAP order.

- **UCP** (main branch, 20 November 2026): `card` is the only payment instrument with a defined schema. Its Split Payments extension divides a total across instruments by amount and priority, with no idea of which items are eligible for which tender. EBT and SNAP appear nowhere in the spec.
- **ACP** (version 2026-04-17): the payment method is `card`, with funding type limited to credit, debit or prepaid, and checkout completion takes a single payment instrument. No EBT.

Every SNAP online order needs three things: an EBT instrument, a flag on each line item saying whether SNAP can pay for it, and a split that puts eligible food on EBT and everything else on a card. Neither protocol has any of them. The same gap blocks HSA and FSA cards, which also pay only for eligible items, so one design would serve all three.

## Limits

- **One assistant, one wave.** Every answer came from Gemini 3.8 Flash with Google Search over two days. Other assistants, and Gemini next month, may differ. The study is built to repeat monthly and to add assistants.
- **One city per state.** The largest city is where a chain is most likely to trade. Smaller towns and rural areas have fewer chain stores, so the city-level error may be larger there. I have not tested that.
- **The coder is a model too.** One Gemini call coded each answer. The hand check caught one coding slip: an Oklahoma City Costco answer that opened with "No" but whose bottom line was "yes, through Same-Day". I have not hand-checked a random sample of agreements.
- **City coverage is estimated.** "Served" means a store under the chain's name within about 20 miles of the city centre, judged from store locators, with distances estimated rather than measured. Walmart and Kroger pages blocked direct fetches, so those rows rest on search snapshots of their store pages, and most ALDI rows rest on a third-party store directory.
- **Delivery reach is not tested.** I placed no orders and entered no addresses, so cross-border delivery cases are left out rather than scored.
- **Gopuff is left out of the headline.** Its state list could only come from USDA's incomplete pages, so its 8 wrong yes answers are reported but not trusted.

## What should change

- **Assistant makers:** when a shopper gives a city, check that a store under that name serves it before saying yes, and end any SNAP shopping answer with one line telling the shopper to confirm their address on the store's site or USDA's list. Both fixes target the only errors this study found.
- **Retailers:** publish EBT online availability by ZIP code, not by state, on a page assistants can read. Safeway in Idaho, Kroger in Missouri and Sprouts in Kansas each trade in only one corner of the state.
- **USDA:** reconcile the state "Stores Accepting SNAP Online" pages with retailers' own policies, starting with Kroger.
- **UCP and ACP maintainers:** add an EBT tender with item-level eligibility and an eligible-items split, designed so HSA and FSA cards can use it too.

## Next

I plan to repeat the 624 questions monthly, add other assistants with live search, and add a second, smaller city in each state to test whether the city-level error grows outside the largest metros. Every prompt, full answer with its search sources, code, the three-layer answer key and the scoring code are in this repository.

## Sources

- USDA, [SNAP online purchasing](https://www.fns.usda.gov/snap/online-purchasing-pilot) and the state "Stores Accepting SNAP Online" pages, read through Internet Archive captures from 27 December 2025 to 10 June 2026 and live on 23 November 2026
- Retailer SNAP online pages: [Walmart](https://www.walmart.com/cp/snap-online/1465096), [Amazon](https://www.aboutamazon.com/news/retail/snap-ebt-benefits-amazon), [ALDI](https://aldi.us/about-us/snap-ebt-payment), [Kroger](https://www.kroger.com/i/snap-ebt-faq), [Safeway](https://www.safeway.com/shopping-guides/services-and-information/how-to-use-snap-ebt-at-safeway-in-store-online-and-drive-up-go-x1ejqp), [Whole Foods](https://www.wholefoodsmarket.com/customer-service/topics/grocery-delivery-and-pickup), [Sprouts](https://www.sprouts.com/faqs/page/5/), [Instacart (Costco, Publix)](https://www.instacart.com/ebt-snap), [Gopuff](https://www.gopuff.com/newsroom/community-impact/gopuff-becomes-first-instant-commerce-company-to-accept-snap-ebt-nationwide)
- City coverage: each retailer's store locator and local news, one source per row in `data/reference/city/`
- [Universal Commerce Protocol](https://github.com/Universal-Commerce-Protocol/ucp) and [Agentic Commerce Protocol](https://github.com/agentic-commerce-protocol/agentic-commerce-protocol) specifications
