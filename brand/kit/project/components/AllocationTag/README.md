# AllocationTag

A small filled block in a transaction row that says how the purchase is split.

The consumer provides the allocation and, for a personal one, the person's name. Markup: `<span class="tag tag-<allocation>">`.

- Shared: `field-1`, text "Shared".
- Personal: `field-2`, text is the person's name ("Alex"), never "Personal".
- Outlay: `field-3`, text "Outlay".
- Excluded: no fill, `muted`, struck through: it doesn't count as spending.

Do:
- Always show the word; the fill only helps scanning.
- Make the whole row clickable to edit the allocation; the tag itself is not a button.

Don't:
- Use these fills for anything else in a table, or round the tag into a pill.
