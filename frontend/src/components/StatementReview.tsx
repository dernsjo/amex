import { useCallback, useEffect, useRef, useState } from "react";
import {
    dayName,
    errorMessage,
    getStatementReview,
    getStatementTransactions,
    kr,
    monthName,
    updateTransactions,
} from "../api";
import type { Account, StatementReview as Review, Transaction, TransactionChanges } from "../api";
import { Segmented } from "./ui";

interface Props {
    accountId: number;
    importId: number;
    accounts: Account[];
    categoriesFor: (account: Account | undefined) => string[];
    onChanged: () => Promise<void>; // the app's transactions changed
    onSettle: (account: Account, period: string | null) => void;
    onBack: () => void;
}

/** A row's choice: "shared", "outlay", "excluded", or "p<user id>" for one person's. */
type Choice = string;

const choiceOf = (t: Transaction): Choice => (t.allocation === "personal" ? `p${t.member_id}` : t.allocation);

const changesFor = (choice: Choice): TransactionChanges =>
    choice.startsWith("p") ? { allocation: "personal", member_id: Number(choice.slice(1)) } : { allocation: choice as Transaction["allocation"] };

/** The scope's categories, plus the current one if it isn't among them. */
const categoryOptions = (names: string[], current: string) => (names.includes(current) ? names : [current, ...names]);

/**
 * Going through one statement: say whose each purchase is with one tap (or one key), and watch
 * what each person pays add up beside it. Then on to the settlement.
 */
const StatementReview = ({ accountId, importId, accounts, categoriesFor, onChanged, onSettle, onBack }: Props) => {
    const [rows, setRows] = useState<Transaction[]>([]);
    const [review, setReview] = useState<Review | null>(null);
    const [uncheckedOnly, setUncheckedOnly] = useState(false);
    const [active, setActive] = useState<number | null>(null); // the row the keys act on
    const [error, setError] = useState<string | null>(null);
    const [busy, setBusy] = useState(false);
    const rowRefs = useRef(new Map<number, HTMLLIElement>());

    const account = accounts.find((a) => a.id === accountId);
    const members = account?.members ?? [];
    const options = [
        { value: "shared", label: "Shared" },
        ...members.map((m) => ({ value: `p${m.user_id}`, label: m.display_name })),
        { value: "outlay", label: "Outlay" },
        { value: "excluded", label: "Not spending" },
    ];

    const load = useCallback(async () => {
        const [list, summary] = await Promise.all([getStatementTransactions(importId), getStatementReview(accountId, importId)]);
        // In the statement's own order.
        list.sort((a, b) => a.booked_on.localeCompare(b.booked_on) || a.id - b.id);
        setRows(list);
        setReview(summary);
        return list;
    }, [accountId, importId]);

    useEffect(() => {
        load()
            .then((list) => setActive(list.find((t) => !t.reviewed)?.id ?? list[0]?.id ?? null))
            .catch((e) => setError(errorMessage(e)));
    }, [load]);

    const shown = uncheckedOnly ? rows.filter((t) => !t.reviewed || t.id === active) : rows;

    /** Send changes, then move on to the next row nobody has checked. */
    const save = useCallback(
        async (updates: ({ id: number } & TransactionChanges)[], advanceFrom?: number) => {
            setError(null);
            setBusy(true);
            try {
                const changed = await updateTransactions(updates);
                const byId = new Map(changed.map((t) => [t.id, t]));
                const next = rows.map((t) => byId.get(t.id) ?? t);
                setRows(next);
                if (advanceFrom !== undefined) {
                    const from = next.findIndex((t) => t.id === advanceFrom);
                    const after = [...next.slice(from + 1), ...next.slice(0, from)].find((t) => !t.reviewed);
                    setActive(after?.id ?? advanceFrom);
                }
                setReview(await getStatementReview(accountId, importId));
                onChanged();
            } catch (e) {
                setError(errorMessage(e));
            } finally {
                setBusy(false);
            }
        },
        [rows, accountId, importId, onChanged],
    );

    /** Choosing what it already is confirms it as it is. */
    const choose = useCallback(
        (t: Transaction, choice: Choice) =>
            save([{ id: t.id, ...(choice === choiceOf(t) ? {} : changesFor(choice)), reviewed: true }], t.id),
        [save],
    );

    const checkTheRest = () => {
        const rest = rows.filter((t) => !t.reviewed);
        if (rest.length) save(rest.map((t) => ({ id: t.id, reviewed: true })));
    };

    // Keys: S shared, 1–9 a person, O outlay, X not spending, Enter/space as it is, ↓/J and ↑/K to move.
    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            const target = e.target as HTMLElement;
            if (e.metaKey || e.ctrlKey || e.altKey || ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName)) return;
            const index = shown.findIndex((t) => t.id === active);
            const t = shown[index];
            const key = e.key.toLowerCase();
            const move = (delta: number) => {
                const next = shown[Math.min(shown.length - 1, Math.max(0, index + delta))];
                if (next) setActive(next.id);
            };
            let choice: Choice | null = null;
            if (key === "arrowdown" || key === "j") move(1);
            else if (key === "arrowup" || key === "k") move(-1);
            else if (key === "s") choice = "shared";
            else if (key === "o") choice = "outlay";
            else if (key === "x") choice = "excluded";
            else if (/^[1-9]$/.test(key) && members[Number(key) - 1]) choice = `p${members[Number(key) - 1].user_id}`;
            else if ((key === "enter" || key === " ") && target.tagName !== "BUTTON" && t) choice = choiceOf(t);
            else return;
            e.preventDefault();
            if (choice && t && !busy) choose(t, choice);
        };
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [shown, active, members, busy, choose]);

    useEffect(() => {
        if (active !== null) rowRefs.current.get(active)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }, [active]);

    if (!account)
        return (
            <div className="view">
                <p className="alert">This statement's account isn't one you can see.</p>
            </div>
        );

    const left = review ? review.total_count - review.checked_count : 0;
    const period = review?.statement.period ?? null;
    const isCard = review?.account_kind === "credit";
    const categories = categoriesFor(account);

    return (
        <div className="view">
            <div className="view-head">
                <div>
                    <button className="link small" onClick={onBack}>
                        ‹ Import
                    </button>
                    <h1 className="head">
                        {account.name}
                        {period && <span className="muted"> · {monthName(period)}</span>}
                    </h1>
                    <p>Say whose each purchase is. Tap a choice, or use the keys below; the next one comes up by itself.</p>
                </div>
            </div>

            {error && (
                <p role="alert" className="alert">
                    {error}
                </p>
            )}

            <div className="review">
                <section className="block review-list" aria-label="Transactions on this statement">
                    <div className="block-head">
                        <h2>
                            {review ? `${review.checked_count} of ${review.total_count} checked` : "Loading…"}
                        </h2>
                        <Segmented
                            label="Show"
                            value={uncheckedOnly ? "unchecked" : "all"}
                            onChange={(v) => setUncheckedOnly(v === "unchecked")}
                            options={[
                                { value: "all", label: "All" },
                                { value: "unchecked", label: "Not checked" },
                            ]}
                        />
                    </div>
                    {review && review.total_count > 0 && (
                        <div className="progress" aria-hidden="true">
                            <span style={{ width: `${(review.checked_count / review.total_count) * 100}%` }} />
                        </div>
                    )}
                    {shown.length === 0 && rows.length > 0 && <p className="muted">Everything here is checked.</p>}
                    <ul className="review-rows">
                        {shown.map((t) => (
                            <li
                                key={t.id}
                                ref={(el) => {
                                    if (el) rowRefs.current.set(t.id, el);
                                    else rowRefs.current.delete(t.id);
                                }}
                                className={`review-row${t.reviewed ? " checked" : ""}${t.id === active ? " active" : ""}`}
                                onClick={() => setActive(t.id)}
                            >
                                <span className="cell-date">{dayName(t.booked_on)}</span>
                                <span className="review-desc">{t.description}</span>
                                <span className={`review-amount${t.amount_minor < 0 ? " refund" : ""}`}>{kr(t.amount_minor, t.currency)}</span>
                                <select
                                    className="select select-small review-category"
                                    value={t.category ?? "Other"}
                                    onChange={(e) => save([{ id: t.id, category: e.target.value }])}
                                    aria-label={`Category for ${t.description}`}
                                >
                                    {categoryOptions(categories, t.category ?? "Other").map((c) => (
                                        <option key={c}>{c}</option>
                                    ))}
                                </select>
                                <div className="review-choice">
                                    <Segmented
                                        label={`Whose is ${t.description}`}
                                        value={choiceOf(t)}
                                        onChange={(choice) => choose(t, choice)}
                                        options={options}
                                    />
                                    <span className="review-mark">{t.reviewed ? "✓ Checked" : ""}</span>
                                </div>
                            </li>
                        ))}
                    </ul>
                    <p className="small muted keys">
                        Keys: <kbd>S</kbd> shared ·{" "}
                        {members.map((m, i) => (
                            <span key={m.user_id}>
                                <kbd>{i + 1}</kbd> {m.display_name} ·{" "}
                            </span>
                        ))}
                        <kbd>O</kbd> outlay · <kbd>X</kbd> not spending · <kbd>Enter</kbd> keep as it is · <kbd>↓</kbd>{" "}
                        <kbd>↑</kbd> move
                    </p>
                </section>

                <aside className="review-aside panel" aria-label={isCard ? "The bill so far" : "The statement so far"}>
                    <p className="small muted">{isCard ? "The bill so far" : "Each one's part so far"}</p>
                    {review && (
                        <>
                            <ul className="review-split">
                                {review.split.shares
                                    .filter((s) => s.amount_minor !== 0 || review.split.shares.length === 1)
                                    .map((s) => (
                                        <li key={s.user_id}>
                                            <span>{isCard ? `${s.display_name} pays` : s.display_name}</span>
                                            <span className="amt">{kr(s.amount_minor)}</span>
                                        </li>
                                    ))}
                            </ul>
                            <p className="small muted">
                                {kr(review.split.total_minor)} in all
                                {review.split.outlay_minor > 0 &&
                                    `, ${kr(review.split.outlay_minor)} of it outlays in ${review.split.owner.display_name}'s part`}
                            </p>
                            <p className="lead">{left === 0 ? "All checked." : `${left} left to check`}</p>
                            <div className="review-actions">
                                <button className="btn btn-primary" onClick={() => onSettle(account, period)}>
                                    See the settlement
                                </button>
                                {left > 0 && (
                                    <button className="btn" onClick={checkTheRest} disabled={busy}>
                                        Keep the rest as they are
                                    </button>
                                )}
                            </div>
                        </>
                    )}
                </aside>
            </div>
        </div>
    );
};

export default StatementReview;
