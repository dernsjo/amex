# Field

A labelled text input or select: the one place, with tables, where Leva draws a line.

The consumer provides the label, the control and its value. Markup: `<label class="field"><span>Label</span><input class="input"></label>`; selects use `class="select"` in the app.

- Label above the control, in `small` weight 500, `muted`. Write it as a plain question or noun: "Email", "Dates look like", "When the description contains".
- The control: 44px tall, `bg` (white in the app), 1.5px `line` border, square. Hover darkens the border to `muted`; focus makes it `ink` and 2px.
- Lay fields in a wrapping row with the action button at the end, aligned to the controls' bottom edge.

Don't:
- Use placeholders as labels, or float labels inside the control.
- Round the corners or fill the control with `surface`.
