---
name: irl-explain
description: "Explain a technical term, concept, bug, PR, error, or code change through an everyday real-life scenario — supermarket, cafe, post office, bank, clinic, commute — instead of a game, and offer three candidate scenarios BEFORE explaining, each with a one-line summary of how it would carry the mechanism, so the user picks the framing that will actually click. Use when the user invokes /irl-explain, or asks for a real-life, everyday, or non-gaming analogy: \"no gaming\", \"explain it with a real life example\", \"not a game analogy\", \"use something normal\", \"give me a different scenario\". This is the non-gaming sibling of gg-explain — hand off to it when the user wants an analogy but not a game one. If they want no analogy at all (plain bullets, or text destined for a colleague), that is gg-explain's opt-out path, not this skill."
---

# irl-explain

Same engine as `gg-explain`, different register: the explanation rides on an everyday scenario instead of a game mechanic. The analogy **is** the explanation, not decoration on top of one — its job is to carry the actual mechanism, in very few words.

One addition, and it is the reason this skill exists: **the user picks the scenario before you explain.** Which frame clicks is the highest-variance part of any analogy, and the user is the only one who knows. Guessing burns the answer and they end up asking for a different scenario anyway — so ask first, once, cheaply.

## Step 1 — Offer three scenarios, before writing any explanation

Present the candidates with `AskUserQuestion`: three options, or four when a genuinely distinct fourth exists. ("Other" is always available to them automatically, so they can name their own.)

Each option carries:
- **label** — the scenario in 2–4 words: "Supermarket checkout", "Hospital triage", "Post office parcel".
- **description** — *how it would explain the thing*. Name the actual mappings, one or two sentences.

**The description is the entire point of the menu.** "Supermarket" tells the user nothing. "The last carton on the shelf — two shoppers both see it there before either one reaches, so both believe it's theirs" lets them judge whether the frame will carry *before* an answer is spent on it. A menu of bare labels is a menu that cannot be chosen from.

What makes a good set:

- **Three genuinely different worlds.** Supermarket / grocery store / corner shop is one option wearing three hats. Spread across domains: retail, food service, post and delivery, banking, health, school, travel, home and cooking, commuting.
- **Same mechanism, different frames.** Every option must explain the concept *correctly* — the user is choosing what clicks, never what is accurate. If one option would explain it wrong, it isn't an option, it's a mistake.
- **Everyday, not specialist.** Scenarios the user plausibly lives through: queueing, ordering food, posting a parcel, booking an appointment. Not aviation maintenance, commodities trading, or surgery — a scenario they'd have to learn first explains nothing.
- **Lead with a recommendation and say why it's closest.** Put the best-fitting scenario first and mark it `(Recommended)` in the label; its description then carries the reason — which part of the mechanism it holds that the others hold less cleanly. An unranked menu hands the user the comparison you already did. Recommending is not deciding: the other options stay real, equally correct, and equally available.

**Skip the menu** when the user already named a scenario ("explain it like a cafe"), or told you to just pick. Go straight to Step 2 and name the scenario in the tag so they can still redirect.

**A scenario already used earlier in the conversation does not become the default.** Offer the menu again and keep a previously used scenario in it, marked as already used, but let the other two be genuinely new. Carry the prior scenario that best fits the new concept, not simply the most recent — and if none of them map it, say so in a line rather than forcing a wrong option in. Correctness outranks continuity. The frame that carried one concept is often the wrong shape for the next, and silently reusing it is how an answer gets bent to fit a world the user chose for something else.

## Step 2 — Explain inside the chosen scenario

1. **Open with the scenario tag.** First line, standing alone: `[Supermarket]`, `[Post office]`, `[Clinic]`. One tag per answer — one answer lives in one scenario.

2. **Bullets, not prose.** Each bullet is one move: setup → mechanism → consequence → the actual point. **Six bullets is the ceiling for any answer**: 3–5 for a single term; a bug/PR spends the same six across its bold lead-ins (**The bug** / **The fix**), 1–3 each. Nest bullets only to enumerate outcomes. Bullet seven means cut.

3. **Map the mechanism, not the vibe.** Test before writing: could the user ask a follow-up *inside* the scenario ("so what if both cashiers scan it at once?") and still get the technically correct answer? If it breaks on the first follow-up, the scenario is wrong — say so and offer a different one rather than bluffing through.

4. **Register check — avoid the scenario whose everyday word is the technical term.** Queue, buffer, pipeline, bottleneck, backlog, handshake, load, traffic: if the scenario's own vocabulary is the jargon being explained, it defamiliarizes nothing and the analogy is circular. A queue at the bank does not explain a message queue. Pick a scenario whose words are ordinary.

5. **When no everyday scenario maps, say so and explain straight.** One clause — "nothing everyday maps this cleanly —" then plain bullets, no tag. An analogy that carries the first bullet and then evaporates, leaving the rest literal, is worse than none: it spends a bullet, teaches nothing, and makes the answer *look* explained.

6. **Accuracy beats the neatness.** Never bend a fact to make the scenario tidier. If a detail matters — it was one line, it's styling-only, the guard still exists — it survives into the analogy intact.

   **And never invent the facts you weren't given.** A good analogy wants a complete mechanism, so there is real pull to fill in whatever the user left out. If a detail you don't have would make the mapping land, mark it as an assumption in the same breath or leave it out and keep the analogy smaller. A confident guess about the user's own system is the one error they cannot catch from the answer alone: it reads exactly like the parts you did know.

7. **Close with the straight version — and close there.** One sentence, real terminology, zero analogy, prefixed `**Straight version:**`, standing alone under the bullets. Never skip it, and **write nothing after it**. If something is worth saying that isn't part of the explanation, it goes in **one** optional `**Also:**` line placed *above* the closer.

## Shape by ask type

- **Single term** — 3–5 bullets, then the straight version.
- **Bug / fix / PR / incident** — bold lead-ins: `**The bug**`, `**The fix**`, optionally `**Why it's safe**`; 1–3 bullets each, six total.
- **Comparison** — build ONE scenario containing both concepts, one or two bullets per side. Two unrelated scenarios side by side is a fail.
- **Glossary / several terms at once** — one bullet per term sharing a single scenario; fold each term's plain meaning into the same bullet after a dash rather than a footer per term. Offer the menu once for the whole set, not per term.
- **Follow-up asked inside the scenario** — answer *inside* it while the mapping holds. The moment an honest answer needs the scenario's facts or the code's bent, drop it in the open — "the analogy stops here —" — and answer straight.
- **Mid-answer rejection** ("that one's not working for me") — don't defend it. Offer the two scenarios they didn't pick, plus one new one, and record the rejection per below.

## Scenario profile

**Where it lives.** `$AI_TOOLBOX_PRIVATE/profiles/irl-explain.md`, default `~/.config/ai-toolbox/profiles/irl-explain.md`. It is personal, so it is kept outside this repository. Read it before Step 1. If it doesn't exist, create it with the seed families below and an empty picks section.

- **Seed families (untested until the user reacts):** retail and supermarket (shelves, checkout, stock, returns) · food service (orders, kitchen tickets, tables, reservations) · post and delivery (tracking, addresses, failed delivery, signatures) · banking (balances, transfers, holds, statements) · health (appointments, triage, records, referrals) · school (homework, grading, registers) · travel (check-in, boarding, baggage, customs) · home and cooking (recipes, prep, fridge, leftovers) · commuting (lanes, signals, parking, tolls) · admin and paperwork (forms, approvals, filing).

**Recording what you learn** in the profile file. Two different strengths of evidence, and conflating them will corrupt it:

- **A pick is a preference signal, not a confirmation.** Choosing "supermarket" over "clinic" may mean it clicked, or may mean it looked interesting. Log picks as a tally, nothing stronger, and note that marking a recommendation biases them further.
- **A pick that overrides the recommendation is the strongest signal available.** Going against the lead means that frame genuinely clicked harder than your best guess. Weight those above ordinary picks and note what shape of concept it was, in generic terms. Never record project names, tickets or internal features: describe the concept shape only.
- **A reaction is confirmation.** "That worked", "that one's not landing", "I still don't get it": write them into the profile in the same turn, under a confirmed line or a rejected line with the reason. A correction that stays in the conversation is lost when the session ends.

Over time the menu should lead with families that have confirmed hits for that *shape* of concept — but a confirmed hit never overrides Step 2's mechanism test. The closest-fitting scenario still wins.

## Example — the menu, then the answer

**Input:** `/irl-explain` what is a race condition?

**Menu presented** (three options, each naming its mapping):

| Scenario | How it would explain it |
|---|---|
| Joint bank account **(Recommended)** | Two cards withdraw at once; both read a balance of 100 before either deduction posts, so both are approved and the account goes negative. Closest fit because the balance is *literally* the shared state being read and written — the other two need you to accept a shelf or a booking book as a stand-in for it. |
| Supermarket last item | Two shoppers both see the last carton on the shelf before either reaches for it — each is sure it's theirs, and who gets it depends on whose hand arrives first. |
| Restaurant double-booking | Two hosts take a phone reservation for table 6 at the same moment, each reading a book that doesn't yet show the other's booking. |

**After they pick "Joint bank account":**

`[Joint bank account]`
- You and your partner withdraw from the same account at two ATMs in the same second.
- Both machines read the balance — 100 each — before either withdrawal has posted to it.
- Both approve: the balance each machine checked was true when it read it, and stale by the time it acted.
- Nobody did anything wrong; the account let two "check, then act" sequences overlap instead of making the second one wait for the first.

**Straight version:** a race condition is when two concurrent operations read shared state and act on it without locking, so the outcome depends on unpredictable timing.
