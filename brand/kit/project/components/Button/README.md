# Button

A square, flat button whose label names exactly what it does.

The consumer provides the label and the handler. Use `<button class="btn …">`.

- `btn btn-primary` (`accent` fill, `accent-ink` text): the one action a screen exists for: Sign in, Import 112 transactions, Close November 2026. One per screen.
- `btn btn-ink` (`ink` fill): a strong secondary action: Continue with Google, Save in an inline editor, Add account.
- `btn` (`surface` fill): everything else: Cancel, Delete, Undo.
- `btn-small` for actions inside a row or an editor.

Do:
- Name the result with its numbers: "Import 112 transactions", not "Confirm".
- Disable a button whose action can't run, and keep its label honest ("Import 0 transactions").

Don't:
- Round the corners, add icons, shadows or gradients.
- Put two primary buttons on one screen.
- Use a red "danger" button: destructive actions are plain `btn` and go through a confirm dialog that names what is lost.
