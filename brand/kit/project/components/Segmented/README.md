# Segmented

A single choice among two to six short options, drawn as a row of blocks cut by `space-share`.

The consumer provides the options (value and label), the current value, an accessible group label and a change handler. Markup: `<div class="segmented" role="group" aria-label="…">` with one `<button aria-pressed>` per option. In the app it is the `Segmented` component in `frontend/src/components/ui.tsx`.

Use it for: a transaction's allocation (Shared, Personal, Outlay, Excluded), whose it is (Alex, Sam), which account to import into, every month or only this month, Setup's sections.

Do:
- Put a one-line explanation of the chosen option beneath it when the words are terms of art (allocation).
- Keep labels to one or two words in sentence case.

Don't:
- Use it for more than six options (use a select) or for actions (use buttons).
- Colour the chosen segment with the accent: chosen is `ink` on `bg` text.
