import { useCallback, useEffect, useState } from "react";
import { errorMessage, getBudgets, kr, setBudget } from "../api";
import type { BudgetLine, BudgetMonth, Transaction } from "../api";

interface Props {
    householdId: number | null; // null: your own budget
    transactions: Transaction[]; // only to know when spending changed
    categoriesVersion: number; // bumped when categories change
}

interface Draft {
    category: string;
    amount: string; // kronor as typed; empty removes the target
    onlyThisMonth: boolean;
}

const thisMonth = () => {
    const today = new Date();
    return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
};

const monthName = (month: string) =>
    new Date(`${month}-01T00:00:00`).toLocaleDateString("sv-SE", { month: "long", year: "numeric" });

const Bar = ({ spent, target }: { spent: number; target: number | null }) => {
    if (!target) return null;
    const ratio = Math.max(0, spent / target);
    return (
        <div style={{ width: "100%", background: "#eee", height: "8px" }}>
            <div
                style={{
                    width: `${Math.min(ratio, 1) * 100}%`,
                    height: "100%",
                    background: ratio > 1 ? "#c0392b" : "#27ae60",
                }}
            />
        </div>
    );
};

/** Each category's target against spending for one month. */
const BudgetPanel = ({ householdId, transactions, categoriesVersion }: Props) => {
    const [month, setMonth] = useState(thisMonth);
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

    return (
        <div>
            <h3>{householdId ? "Shared budget" : "My budget"}</h3>
            <p>
                {householdId
                    ? "Spending marked shared on the household's accounts."
                    : "Your own share: your personal spending plus your part of each household's shared spending."}
            </p>
            <input type="month" value={month} onChange={(e) => e.target.value && setMonth(e.target.value)} />
            {error && <p role="alert">{error}</p>}
            {budget && (
                <table border={1} style={{ width: "100%", borderCollapse: "collapse", marginTop: "8px" }}>
                    <thead>
                        <tr>
                            <th>Category</th>
                            <th>Target</th>
                            <th>Spent</th>
                            <th>Left</th>
                            <th style={{ width: "30%" }} />
                        </tr>
                    </thead>
                    <tbody>
                        {budget.lines.map((line) => {
                            const editing = draft?.category === line.category ? draft : null;
                            return (
                                <tr key={line.category}>
                                    <td>{line.category}</td>
                                    <td>
                                        {editing ? (
                                            <>
                                                <input
                                                    type="number"
                                                    min="0"
                                                    step="100"
                                                    placeholder="No target"
                                                    value={editing.amount}
                                                    onChange={(e) => setDraft({ ...editing, amount: e.target.value })}
                                                    style={{ width: "7em" }}
                                                />
                                                <select
                                                    value={editing.onlyThisMonth ? "month" : "every"}
                                                    onChange={(e) =>
                                                        setDraft({ ...editing, onlyThisMonth: e.target.value === "month" })
                                                    }
                                                >
                                                    <option value="every">every month</option>
                                                    <option value="month">only {monthName(month)}</option>
                                                </select>
                                                <button onClick={() => handleSave(line)}>Save</button>
                                                <button onClick={() => setDraft(null)}>Cancel</button>
                                            </>
                                        ) : (
                                            <span style={{ cursor: "pointer" }} onClick={() => startEditing(line)}>
                                                {line.target_minor === null ? "Set target" : kr(line.target_minor)}
                                                {line.override_minor !== null && " (this month)"}
                                            </span>
                                        )}
                                        {!editing && line.override_minor !== null && (
                                            <button
                                                title="Go back to the target for every month"
                                                onClick={() => save(() => setBudget(householdId, line.category, month, null))}
                                            >
                                                Reset
                                            </button>
                                        )}
                                    </td>
                                    <td>{kr(line.spent_minor)}</td>
                                    <td>{line.target_minor === null ? "" : kr(line.target_minor - line.spent_minor)}</td>
                                    <td>
                                        <Bar spent={line.spent_minor} target={line.target_minor} />
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                    <tfoot>
                        <tr>
                            <th>Total</th>
                            <th>{kr(budget.target_minor)}</th>
                            <th>{kr(budget.spent_minor)}</th>
                            <th>{kr(budget.target_minor - budget.spent_minor)}</th>
                            <th />
                        </tr>
                    </tfoot>
                </table>
            )}
        </div>
    );
};

export default BudgetPanel;
