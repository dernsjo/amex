Leva is an AI-native personal finance app for people and the households they live in. You import your bank statements, and Leva gives you one clear view of your money: what you spend, against which budget, and how shared costs fall between the people you live with. Next, it lets you ask about that money in plain words, get advice from an AI money expert, and connect the same data to your own agents (Claude first). *Leva* is Swedish for "to live": the brand is about the life the money pays for, not the money itself. Every decision in this system serves one outcome: you understand your money well enough to stop worrying about it.

Tagline: **Money, for the way you live.**

## The idea: the share

The brand has one shape. **A block cut into shares by a 4px gap** (`space-share`). It comes from the product's own data: where a month's money went (each category a share), a budget (spent and left), a household's split weights (3 and 2 is 60/40), a settlement (who carries what). Understanding money is seeing its shares. Use it, and only it, everywhere a designer would reach for a card, a pill or an icon.

- The mark is the share at its simplest: one square cut 18 : 11 on a 32-unit grid with a 3-unit gap, a 60/40 split.
- Data is shown as shares: budget bars, split weights, settlement bars, the 12-month trend. Parts sit side by side, cut by `space-share`, never stacked with borders.
- Choices are shares: the segmented control is a row of blocks with the same gap.
- At large scale the share is the hero: two blocks, cropped by the viewport, in `accent` and `ink`. On the sign-in screen their widths follow a live split slider.
- Never add a second shape. No circles, blobs, waves or icons standing in for the share.

## Content fundamentals

The product is written in English with Swedish money: amounts are formatted `sv-SE` (`1 240,00 kr`), months in English (`November 2026`).

- **Plain and specific.** Say exactly what happens: "Import 112 transactions", "Close November 2026", "Sam pays Alex 2 656,40 kr". Buttons name the action, never "Submit" or "OK".
- **You, not we.** Talk to the person: "Your spending", "Choose a row to change how it's split." Leva refers to itself by name only where a person would ("Leva reads your statements. It never moves money.").
- **Sentence case** everywhere: headings, buttons, labels. No all-caps labels, no exclamation marks, no emoji.
- **Money is exact.** Show öre (`9 314,75 kr`), never round a figure someone may transfer. Negative balances use a real minus sign (`−2 656,40 kr`).
- **The household's words.** *Shared*, *personal*, *outlay*, *excluded*, *settle up*, *close the month*, *even* ("Everyone is even."). Avoid *transaction allocation*, *ledger entry*, *sync*, *financial wellness*, *optimize*.
- **Calm, never alarming.** Over budget is a fact with a next step ("Groceries is 640 kr over. 9 days left."), not a warning. No warning icons, no "Uh-oh".
- **Errors say what to do.** "Enter an amount in kronor, or leave it empty for no target." No apologies.
- **Never invent proof.** No customer quotes, logos or statistics in product or marketing copy until they exist.

### AI in Leva

AI reaches Leva in three ways. They share one voice and one set of rules.

1. **Ask Leva.** A question box over your own data: "What did we spend on eating out since summer?" The answer is a sentence, the figure, and the shares behind it, drawn with the same components as the app.
2. **The expert.** Advice written by an AI money expert from your real figures: a budget that fits last quarter, a fairer split for a couple whose incomes changed, what a subscription costs per year. The expert is always labelled as AI, shows the numbers it used, and never pretends to be a licensed adviser.
3. **Connectors.** Your own agents (Claude first, over MCP) read the same data with your permission and can propose changes. The connector's avatar is the mark (`leva-mark.svg`); its name is "Leva".

Rules for anything an AI says on Leva's behalf:

- Always name the **scope and month**: "In Home, November 2026, shared spending is 9 314,75 kr."
- Quote amounts **exactly as Leva stores them** (öre, `sv-SE`), never rounded or converted unless asked. Show the figures any advice rests on.
- **Reads are free; writes are proposals.** An AI may recategorize, re-split or set a budget only after the person confirms, and it says what changed ("Moved 3 transactions from Other to Groceries").
- **Advice is a suggestion with its reason**, in the second person and the conditional: "You could lower Eating out to 2 500 kr. You've stayed under that in 4 of the last 6 months." Never "you should", never guarantees, never investment, tax or legal advice.
- **Honest about being AI.** Say "I" only inside a chat; label generated text ("Suggested by Leva AI"); say plainly when the data can't answer ("Your statements only go back to March.").
- Leva **never moves money**. No AI copy may suggest a transfer or payment was made.
- **Privacy is the default.** A connector only sees the scopes the person granted; a household member's personal spending is never shown to anyone else.

## Visual foundations

### Colour

One paper ground, black ink, one magenta accent; flat pastel fields for whole tiles.

- Page ground `bg`; one step down for rails, rows and resting buttons `surface`; hover `surface-2`. Surfaces are told apart by tone steps, never by lines or shadows.
- Running text in `ink`. `muted` only for secondary notes (dates, hints), never for body copy.
- `accent` (magenta) is the action: the primary button, the current nav marker, the chosen month, the amount someone owes, an over-budget share. At most one or two places per screen. Text on it is `accent-ink`. Accent text on `surface` uses `accent-press` for contrast.
- Fields `field-1` … `field-4` fill whole tiles that carry one statement: the month's total (`field-1`), the settlement (`field-2`), the budget total (`field-3`), the drop zone while dragging (`field-4`). Text on a field is always `ink`. Never put two of the same field side by side.
- Members keep one colour each, by their position in the household: `member-1` … `member-4`. This order was checked for colour-blind separation; always label members by name as well (direct labels inside the share, a swatch beside the name).
- `line` exists only for real form fields and real tables.
- No gradients, no glows, no violet, no cream-and-terracotta.

### Type

One family, Chillax, at five sizes. Nothing in between.

- `display` (100px, 600): one figure per screen, the month's total or the closing verdict.
- `head` (64px, 600): view titles and the settlement sentence.
- `lead` (26px, 500): block headings and statements.
- `body` (19px, 400): running text, table cells.
- `small` (14px, 400): labels, dates, hints. Never smaller.
- Display tracking is tight (-0.035em); text tracking 0. Figures use tabular numerals wherever they line up.
- Headlines run two lines at most. No styled accent words inside a headline.

### Space and layout

- One page margin (`space-margin`, 16–40px fluid) and one gap between blocks (`space-block`). Inside a block, `space-2` and `space-3`.
- The app shell: a `surface` rail on the left (wordmark, scope switcher, five or six plain nav links, the person at the bottom), the view on `bg`. On a phone the rail becomes a top band with wrapping tabs.
- Left-aligned by default. A view opens with its one large thing (the figure, the verdict, the drop zone), then the detail.

### Corners, borders, shadows

- **Square corners everywhere** (`radius-none`): buttons, fields, tiles, tags, the mark.
- Borders only on form fields (`line`, ink on focus) and table rows.
- No shadows on anything at rest. `shadow-dialog` is the one shadow, for a modal dialog that truly floats.

### Motion

- Parts of a view rise 20px and fade in, staggered 70ms, once.
- Shares grow from their left edge on first paint; trend bars grow from the baseline.
- Controls press to 0.97 scale in 140ms. Hover is a tone step in 180ms.
- The sign-in hero opens with a shutter (clip from the right, 1.1s) and its two blocks follow the split slider.
- Everything has a `prefers-reduced-motion` fallback that keeps content and drops travel.

### Imagery and iconography

- The product's pictures are its own interface: real figures, real shares. No stock photos of families with laptops, no illustrations of coins.
- There is no icon set. Use words ("Delete", "Undo", "‹ ›" for month stepping) and the share. If an icon becomes unavoidable, draw it from squares on the 32-unit grid.

## Logo

Files are in the **Logos** asset group.

- **Lockup** (`leva-lockup.svg`): the mark, then the wordmark *leva* in lowercase Chillax Semibold at -0.04em, outlined. The mark is as tall as the wordmark's ascender, with a gap of half its height, so the ink block never reads as a second *l*. Use it in the app rail, on sign-in and in documents.
- **Mark** (`leva-mark.svg`): favicon, app icon (`leva-app-icon.svg`, the mark on `bg` with 22% padding), the avatar of the Leva connector and of Leva AI in chat, anywhere under 24px tall.
- **On dark** (`-on-dark` files): the ink block becomes `bg`; magenta stays.
- **Mono** (`leva-mark-mono-ink.svg`): one-colour printing only.
- Clear space: the width of the mark's ink block on every side. Minimum size: the mark at 16px, the lockup at 20px tall.
- Don't recolour the blocks, swap their order, round their corners, change the 18 : 11 proportion, put the mark on a field that matches either block, or set the wordmark in another face or in capitals.
