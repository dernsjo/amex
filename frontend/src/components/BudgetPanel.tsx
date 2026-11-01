import { useCallback, useEffect, useState } from "react";
import { errorMessage, getBudgets, kr, monthName, setBudget } from "../api";
import type { BudgetLine, BudgetMonth, Transaction } from "../api";
import { MonthStepper, Segmented, ShareBar } from "./ui";

interface Props {
    householdId: number | null; // null: your own budget
    month: string; // YYYY-MM
    onMonthChange: (month: string) => void;
    transactions: Transaction[]; // only to know when spending changed
    categoriesVersion: number; // bumped when categories change
}

interface Draft {
    category: string;
    amount: string; // kronor as typed; empty removes the target
    onlyThisMonth: boolean;
}

/** Spent against target as the motif: spent in ink, what's left in grey, anything over in the accent. */
const budgetParts = (spent: number, target: number | null) =>
    target
        ? [
              { value: Math.min(spent, target), className: "spent" },
              { value: Math.max(0, target - spent), className: "rest" },
              { value: Math.max(0, spent - target), className: "over" },
          ]
        : [{ value: Math.max(spent, 1), className: "rest" }];

/** Each category's target against spending for one month. */
const BudgetPanel = ({ householdId, month, onMonthChange, transactions, categoriesVersion }: Props) => {
    const [budget, setBudgetMonth] = useState<BudgetMonth | null>(null);
    const [draft, setDraft] = useState<Draft | null>(null);
    const [error, setError] = useState<string | null>(null);

    const fetchBudget = useCallback(async () => {
        setBudgetMonth(await getBudgets(householdId, month));
    }, [householdId, month]);

    useEffect(() => {
        fetchBudget().catch((e) => setError(errorMessage(e)));
    }, [fetchBudget, transactions, categoriesVersion]);

    const startEditing = (line: BudgetLine) =>
        setDraft({
            category: line.category,
            amount: line.target_minor === null ? "" : String(line.target_minor / 100),
            onlyThisMonth: line.override_minor !== null,
        });

    const save = async (changes: () => Promise<void>) => {
        setError(null);
        try {
            await changes();
            setDraft(null);
            await fetchBudget();
        } catch (e) {
            setError(errorMessage(e));
        }
    };

    const handleSave = (line: BudgetLine) => {
        if (!draft) return;
        const amount = draft.amount.trim() === "" ? null : Math.round(parseFloat(draft.amount) * 100);
        if (amount !== null && !(amount >= 0)) {
            setError("Enter an amount in kronor, or leave it empty for no target");
            return;
        }
        save(async () => {
            if (draft.onlyThisMonth) return setBudget(householdId, line.category, month, amount);
            await setBudget(householdId, line.category, null, amount);
            // A target for every month replaces this month's own one.
            if (line.override_minor !== null) await setBudget(householdId, line.category, month, null);
        });
    };

    const left = budget ? budget.target_minor - budget.spent_minor : 0;

    return (
        <div className="view">
            <div className="view-head">
                <div>
                    <h1 className="head">{householdId ? "Shared budget" : "Your budget"}</h1>
                    <p>
                        {householdId
                            ? "Spending marked shared on the household's accounts."
                            : "Your own share: your personal spending plus your part of each household's shared spending."}
                    </p>
                </div>
                <MonthStepper month={month} onChange={onMonthChange} />
            </div>

            {error && (
                <p role="alert" className="alert">
                    {error}
                </p>
            )}

            {budget && (
                <>
                    <section className="total tile tile-3 rise" aria-label="Total">
                        <p className="total-figure">{budget.target_minor > 0 ? kr(Math.abs(left)) : kr(budget.spent_minor)}</p>
                        <p className="total-meta">
                            {budget.target_minor === 0
                                ? `spent in ${monthName(month)}, with no targets set yet`
                                : left >= 0
                                  ? `left of ${kr(budget.target_minor)} for ${monthName(month)}`
                                  : `over a budget of ${kr(budget.target_minor)}`}
                        </p>
                        {budget.target_minor > 0 && (
                            <ShareBar className="grow-x" parts={budgetParts(budget.spent_minor, budget.target_minor)} />
                        )}
                    </section>

                    <section className="block">
                        <div className="block-head">
                            <h2>By category</h2>
                            <span className="small muted">Choose a target to change it</span>
                        </div>
                        <ul className="budget">
                            {budget.lines.map((line, i) => {
                                const editing = draft?.category === line.category ? draft : null;
                                const lineLeft = line.target_minor === null ? null : line.target_minor - line.spent_minor;
                                return (
                                    <li key={line.category} className="budget-row rise" style={{ ["--i" as string]: Math.min(i, 10) }}>
                                        <span className="cat">{line.category}</span>
                                        <ShareBar parts={budgetParts(line.spent_minor, line.target_minor)} />
                                        <span className="fig">
                                            {kr(line.spent_minor)} of{" "}
                                            <button className="target-btn" onClick={() => startEditing(line)}>
                                                {line.target_minor === null ? "no target" : kr(line.target_minor)}
                                            </button>
                                            {line.override_minor !== null && <span className="muted"> this month</span>}
                                        </span>
                                        <span className={`fig${lineLeft !== null && lineLeft < 0 ? " left-over" : ""}`}>
                                            {lineLeft === null ? "" : lineLeft >= 0 ? `${kr(lineLeft)} left` : `${kr(-lineLeft)} over`}
                                        </span>
                                        {editing && (
                                            <form
                                                className="budget-edit"
                                                onSubmit={(e) => {
                                                    e.preventDefault();
                                                    handleSave(line);
                                                }}
                                            >
                                                <label className="field">
                                                    <span>Target in kronor</span>
                                                    <input
                                                        className="input"
                                                        type="number"
                                                        min="0"
                                                        step="100"
                                                        placeholder="No target"
                                                        value={editing.amount}
                                                        onChange={(e) => setDraft({ ...editing, amount: e.target.value })}
                                                        autoFocus
                                                    />
                                                </label>
                                                <Segmented
                                                    label="Applies to"
                                                    value={editing.onlyThisMonth ? "month" : "every"}
                                                    onChange={(v) => setDraft({ ...editing, onlyThisMonth: v === "month" })}
                                                    options={[
                                                        { value: "every", label: "Every month" },
                                                        { value: "month", label: `Only ${monthName(month)}` },
                                                    ]}
                                                />
                                                <div className="edit-actions">
                                                    <button type="submit" className="btn btn-ink btn-small">
                                                        Save
                                                    </button>
                                                    <button type="button" className="btn btn-small" onClick={() => setDraft(null)}>
                                                        Cancel
                                                    </button>
                                                    {line.override_minor !== null && (
                                                        <button
                                                            type="button"
                                                            className="btn btn-small"
                                                            onClick={() => save(() => setBudget(householdId, line.category, month, null))}
                                                        >
                                                            Back to every month's target
                                                        </button>
                                                    )}
                                                </div>
                                            </form>
                                        )}
                                    </li>
                                );
                            })}
                        </ul>
                    </section>
                </>
            )}
        </div>
    );
};

export default BudgetPanel;
