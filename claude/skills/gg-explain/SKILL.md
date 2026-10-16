---
name: gg-explain
description: Explain any technical term, concept, bug, PR, error, or code change in short bullet points built on the game mechanic that maps closest to it (Pokémon, MMOs, MOBAs, Minecraft, roguelikes — chosen by fit, and named when it helps) — offering three candidate mappings first, the closest marked as recommended, so the user picks the framing that will actually click — and closing gaming-framed answers with one plain "Straight version" line that uses the real terminology. Use this whenever the user asks for a simple, plain, or quick explanation — "what is X", "in simple terms", "eli5", "what does this mean", "dumb it down", "explain this bug/PR/fix to me" — even when they don't mention games; gaming framing is this user's preferred explanation style. Definitely use it when they say "gaming terms", "like a game", or "/gg-explain". Skip the gaming frame (plain short bullets only) when they say "serious", when they want no analogy at all, or when the text is destined for someone else (a PR description, a doc, a message to a colleague). If they want an analogy but not a gaming one — "no gaming", "a real-life example" — that is the sibling skill `irl-explain`, not this one.
---

# gg-explain

The user is a developer who groks concepts fastest through game mechanics. The analogy **is** the explanation, not decoration on top of one — so its job is to carry the actual mechanism of the concept, in very few words.

## Step 1 — Offer three mappings, before writing any explanation

Present three candidates with `AskUserQuestion`, all drawn from the player profile's pool — a game the user doesn't play explains nothing.

Each option carries:
- **label** — game and mechanic in 2–5 words: "Pokémon party vs PC box", "MOBA cooldown", "Save scumming". Mark the closest fit `(Recommended)`.
- **description** — *how it would explain the thing*: name the actual mapping, one or two sentences. The recommended one also says what makes it closest.

**The description is the entire point of the menu.** "Pokémon" tells the user nothing; "your party is six slots you carry because a Center trip is slow, and the boxed copy drifts out of sync with it" lets them judge whether the frame will carry before an answer is spent on it.

What makes a good set:

- **Three genuinely different mechanics**, ideally different games. Three flavours of one loot-drop mechanic is a single option wearing three hats.
- **Every option must be correct.** They are choosing what clicks, never what is accurate. An option that would explain it wrongly is a mistake, not a choice.
- **All in-pool at the profile's stated depth** — generic MMO vocabulary only, Minecraft light-touch, MOBA standard. An out-of-pool option is worse than a weaker in-pool one.
- **Don't pad.** If only one in-pool mechanic genuinely maps, say so and use it. If none map, take rule 3's escape hatch instead of inventing a menu.

**Skip the menu** when the user names a game, says to just pick, or asked in passing while working on something else — a picker that interrupts other work costs more than it saves. Explain directly and name the game in the tag so they can still redirect.

**A mapping already used earlier in the conversation does not become the default.** Offer the menu again and keep a previously used mapping in it, marked as already used, but let the other two be genuinely new. Carry the prior mapping that best fits the new concept, not simply the most recent — and if none of them map it, say so in a line rather than forcing a wrong option in. Correctness outranks continuity. The frame that carried one concept is often the wrong shape for the next, and silently reusing it is how an answer gets bent to fit a world the user chose for something else.

## Step 2 — Explain inside the chosen game

1. **Bullets, not prose.** Each bullet is one move of the explanation: setup → mechanism → consequence → the actual point. **Six bullets is the ceiling for any answer**: 3–5 for a single term; a bug/PR spends the same six across its bold lead-ins (**The bug** / **The fix**), 1–3 each. Nest bullets only to enumerate outcomes (e.g. success/warning/error). If you're writing bullet seven, cut — brevity is the brief.

   **Open with the game tag**: the first line of every gaming-framed answer is the game in brackets — `[Pokémon]`, `[Dota]`, `[Minecraft]`, or `[any MMO]` / `[any RPG]` for cross-game mechanics — standing alone before the first bullet, so the reader loads the right game into their head before reading. One tag per answer, because one answer lives in one game world (the Comparison shape below depends on this).

2. **The analogy must map the mechanism, not the vibe.** Test before writing: could the user ask a follow-up question *inside* the analogy ("so what happens if two players do it at once?") and the analogy still give the technically correct answer? If it breaks on the first follow-up, pick a different game mechanic. A label swap ("a cache is like a treasure chest") maps nothing — where's the speed/staleness tradeoff? A real mapping: cache = your Pokémon party vs. the PC box — six slots you keep on hand because a Center trip is slow, small on purpose, and holding a copy that can go stale relative to the box.

3. **Candidates come from the closest mechanics, not a favorite genre.** Step 1 offers the top three and recommends the closest; this rule is how you find them. Scan for games whose *actual mechanic* mirrors the concept's mechanism — Pokémon's party-vs-PC-box for caching, the Pokédex sort for database indexes, MMO item duping for race conditions, save scumming for rollbacks, MOBA cooldowns for rate limiting, Hades' die-retry-keep-meta-progress loop for checkpointed retries, Balatro's joker chain (each joker transforms the score in order) for middleware/composed pipelines. Name the game when it sharpens the mapping. No genre gets a default: an analogy from a "preferred" genre with a loose mapping loses to any game with a tight one. One register check: if the game's own vocabulary is engineering vocabulary (throughput, pipeline, buffer, queue), it can't defamiliarize the concept — pick a mechanic whose words actually sound like a game.

   **When nothing in the pool maps, say so and explain straight.** One clause is enough — "no clean game mapping for this one —" then plain bullets, no tag. An analogy that carries the first bullet and then evaporates, leaving the rest literal, is the exact failure this skill exists to prevent: it spends a bullet, teaches nothing, and makes the answer *look* explained. Reaching for a loose mapping under pressure to produce one is worse than admitting there isn't one.

4. **Accuracy beats the joke.** Never bend the facts to land a pun. If a detail matters (it was 1 line, it's styling-only, the guard still exists), it survives into the analogy intact.

   **And never invent the facts you weren't given.** A good analogy wants a complete mechanism, so there is real pull to fill in whatever the user left out — how their hook resolves arguments, what their endpoint returns when it fails, why their test is red. If a detail you don't have would make the mapping land, either mark it as an assumption in the same breath ("assuming it matches the raw string —") or leave it out and keep the analogy smaller. A confidently stated guess about the user's own system is the one error they cannot catch from the answer alone: it reads exactly like the parts you did know.

5. **Close with the straight version — and close there.** One sentence, real terminology, zero analogy, prefixed `**Straight version:**` — a standalone line under the bullets, not a bullet. The analogy teaches the shape; the closer teaches the words. Never skip it on a gaming-framed answer, and **write nothing after it**: no trailing paragraph, no "worth knowing" addendum. It is the last line of the explanation. (A single-line offer to do the next thing, when the conversation needs one, is a separate conversational move — not a place to resume explaining.)

   If you have something worth saying that isn't part of the explanation — a caveat, a consequence, something you noticed while answering — it goes in **one** optional `**Also:**` line placed *above* the closer. One line, not a paragraph. If it needs more room than that, it is its own answer and the user will ask for it.

## Player profile

Rule 3's "closest game" is chosen **only from the user's player profile**: an analogy from a game the user doesn't play explains nothing.

**Where it lives.** `$AI_TOOLBOX_PRIVATE/profiles/gg-explain.md`, default `~/.config/ai-toolbox/profiles/gg-explain.md`. It is personal, so it is kept outside this repository. Read it before Step 1.

**No profile yet?** Ask once, in one question: which games or genres they play, and how deep (famous mechanics only, or the systems too). Save the answer as the profile with these headings, then continue:
- **Pool:** games and genres, each with its depth ("generic MMO vocabulary only", "Minecraft light touch", "MOBA standard").
- **Shape specialists:** which game owns which concept shape (for example storage and lookup, timing and limits), once evidence shows it.
- **Out of pool:** games and terms that do not land, with the reason.
- **Confirmed vocabulary** and **banned terms.**
- **Tiebreak:** closest mechanic wins unless the user says otherwise.

**Keeping the profile current.** When the user says an analogy didn't land, or confirms one did, edit the profile file in the same turn: add the game or mechanic to the out-of-pool list with the reason, or record the confirmed hit next to its shape. A correction that stays in the conversation is lost when the session ends. One data point justifies one edited line, not a new diagnostic round.

A pick is a preference signal, not a confirmation, and marking one `(Recommended)` biases it further, so log picks as a tally only. **A pick that overrides the recommendation is the strongest signal available**: going against the best guess means that frame genuinely clicked harder. Weight those above ordinary picks and note the shape of concept they applied to.

## Shape by ask type

- **Single term** ("what is a race condition?") — 3–5 bullets, then the straight version.
- **Bug / fix / PR / incident** ("what's the bug and the fix?") — bold lead-ins per part: `**The bug**`, `**The fix**`, optionally `**Why it's safe**` when review/rollout context exists; 1–3 bullets each, six total.
- **Comparison** ("auth vs authz?") — build ONE game world that contains both concepts, one or two bullets per side inside that world. Two unrelated analogies side by side is a fail.
- **Glossary / several terms at once** — one bullet per term, ideally sharing a single game world; fold each term's straight version into the same bullet after a dash rather than writing a footer per term. Brevity per term beats completeness.
- **Follow-up asked inside the analogy** ("so what happens if two players do it at once?") — answer *inside* the game world for as long as the mapping holds; that is exactly what rule 2's test buys you. The moment an honest answer would require bending the game's facts or the code's, drop the analogy in the open — "the analogy stops here —" — and answer straight. Silently switching registers mid-answer is what makes an analogy untrustworthy.
- **Opt-out** ("serious", no analogy wanted, or the output is for someone else) — plain simple bullets, same brevity, no analogy, no straight-version footer (the whole thing is already straight).
- **Wrong register, not wrong idea** ("no gaming", "give me a real-life example") — they still want an analogy, just not a game. Hand off to `irl-explain`, which offers a scenario menu first. Don't drop to plain bullets: that answers a question they didn't ask. Text destined for someone else stays plain either way.

## Examples

**Input:** what is a race condition? simple terms

**Menu presented** (three mappings, closest first):

| Mapping | How it would explain it |
|---|---|
| MMO item duping **(Recommended)** | Two players loot the same chest on the same server tick; each checks "still closed? yes" before the other's loot registers, so both walk away with it. Closest fit because the chest *is* the shared state, and the check-then-act overlap is visible in one sentence. |
| Save scumming | You reload an old save and replay a decision, not realising a second save was written in between — which file wins depends on the order they landed, not on what you intended. |
| MOBA cooldown overlap | Two abilities read the same mana pool in the same instant; both see enough, both fire, and the pool goes negative. |

**After they pick "MMO item duping":**

`[any MMO]`
- Item duping is the classic: two clients loot the same chest on the same server tick.
- Each one checks "chest still closed? yes" before the other's loot registers → both grab the item.
- Sometimes it dupes, sometimes one player gets a phantom error — the outcome depends on which packet lands first.
- The bug isn't either player; the server let two "check, then act" sequences interleave instead of queueing them.

**Straight version:** a race condition is when two concurrent operations read shared state and act on it without locking, so the outcome depends on unpredictable timing.

---

**Input:** eli5 what a cache is

**Output:**
`[Pokémon]`
- Your party is six slots you carry; the PC box holds everything else you own.
- You keep six on hand because walking back to a Center costs time — that trip is the whole reason the party exists.
- Six is small on purpose: a party as big as the box would defeat the point of a fast carried set.
- The catch is staleness — train the boxed copy and the one in your party no longer matches it.

**Also:** deciding who gets deposited when you catch a seventh is an eviction policy.

**Straight version:** a cache is a small, fast-access copy of data kept close to where it's used, trading capacity and freshness for speed — a cached entry can go stale relative to its source, and an eviction policy decides what leaves when it's full.

---

**Input:** what does this PR do? in simple terms *(a one-line CSS change making a delete button solid red)*

**Output:**
`[any RPG]`
**The bug**
- The Delete button wore the wrong skin — hollow red outline, like a greyed-out side-quest option, when the design calls for solid "ARE YOU SURE?" boss-fight red.

**The fix**
- One-line cosmetic patch: the button's variant swapped from hollow to solid.
- No gameplay logic changed — clicking still just opens the confirm dialog, whose real point-of-no-return button was already solid red and guarded.

**Straight version:** a 1-file, 1-line change of a button's style variant from `outline-danger` to `danger`; presentation only, the confirmation flow is untouched.
