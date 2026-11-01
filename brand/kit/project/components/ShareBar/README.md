# ShareBar

The brand's one shape at data scale: parts of a whole, side by side, cut by the 4px `space-share` gap.

The consumer provides the parts (a value each, plus a class or colour and an optional label) and the height through `--share-h`. Parts are `flex-grow` by value with `flex-basis: 0`; a part of zero is left out. In the app it is the `ShareBar` React component in `frontend/src/components/ui.tsx`.

Use it for:
- Budgets: `spent` (`ink`), then `rest` (`surface-2`, or `bg` on a field), then `over` (`accent`) only when spending passed the target.
- Household splits and settlements: one part per member in `member-1` … `member-4`, each labelled with the member's name inside the part.
- The sign-in hero, where two parts at viewport scale follow a live split slider.

Do:
- Put a legend or direct labels beside every share with more than one meaning; colour is never the only signal.
- Let shares grow from the left edge on first paint (900ms, staggered).

Don't:
- Add borders, rounded ends, gradients or a track behind the parts.
- Stack parts vertically or nest shares.
- Use it for more than four members' colours without labels.
