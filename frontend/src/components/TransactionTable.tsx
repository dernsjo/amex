import { useState } from "react";
import { deleteExpense, errorMessage, updateExpense } from "../api";
import type { Expense } from "../api";

interface Props {
    expenses: Expense[];
    paidByOptions: string[];
    categories: string[];
    fetchExpenses: () => Promise<void>;
}

interface Draft {
    id: number;
    paid_by: string;
    category: string;
}

const Select = ({ value, options, onChange }: { value: string; options: string[]; onChange: (v: string) => void }) => (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((option) => (
            <option key={option} value={option}>
                {option}
            </option>
        ))}
    </select>
);

function ExpenseTable({ expenses, paidByOptions, categories, fetchExpenses }: Props) {
    // The row being edited; clicking its Paid By or Category cell starts editing both.
    const [draft, setDraft] = useState<Draft | null>(null);
    const [error, setError] = useState<string | null>(null);

    const startEditing = (expense: Expense) => {
        setDraft({ id: expense.id, paid_by: expense.paid_by, category: expense.category ?? "Other" });
    };

    const handleSave = async (expense: Expense) => {
        if (!draft) return;
        setError(null);
        try {
            const changes = {
                ...(draft.paid_by !== expense.paid_by && { paid_by: draft.paid_by }),
                ...(draft.category !== expense.category && { category: draft.category }),
            };
            if (Object.keys(changes).length > 0) {
                await updateExpense(expense.id, changes);
                await fetchExpenses();
            }
            setDraft(null);
        } catch (e) {
            setError(errorMessage(e));
        }
    };

    const handleDeleteExpense = async (expenseId: number) => {
        setError(null);
        try {
            await deleteExpense(expenseId);
            await fetchExpenses();
        } catch (e) {
            setError(errorMessage(e));
        }
    };

    return (
        <div>
            <h3>Expense Table</h3>
            <p>Click a Paid By or Category value to edit it.</p>
            {error && <p role="alert">{error}</p>}
            <table border={1} style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Description</th>
                        <th>Category</th>
                        <th>Amount</th>
                        <th>Paid By</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {expenses.map((expense) => {
                        const editing = draft?.id === expense.id ? draft : null;
                        return (
                            <tr key={expense.id}>
                                <td>{expense.date}</td>
                                <td>{expense.description}</td>
                                <td>
                                    {editing ? (
                                        <Select
                                            value={editing.category}
                                            options={categories}
                                            onChange={(category) => setDraft({ ...editing, category })}
                                        />
                                    ) : (
                                        <span style={{ cursor: "pointer" }} onClick={() => startEditing(expense)}>
                                            {expense.category ?? "—"}
                                        </span>
                                    )}
                                </td>
                                <td>{expense.amount.toFixed(2)}</td>
                                <td>
                                    {editing ? (
                                        <Select
                                            value={editing.paid_by}
                                            options={paidByOptions}
                                            onChange={(paid_by) => setDraft({ ...editing, paid_by })}
                                        />
                                    ) : (
                                        <span style={{ cursor: "pointer" }} onClick={() => startEditing(expense)}>
                                            {expense.paid_by}
                                        </span>
                                    )}
                                </td>
                                <td>
                                    {editing ? (
                                        <>
                                            <button onClick={() => handleSave(expense)}>Save</button>
                                            <button onClick={() => setDraft(null)}>Cancel</button>
                                        </>
                                    ) : (
                                        <button onClick={() => handleDeleteExpense(expense.id)}>Delete</button>
                                    )}
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}

export default ExpenseTable;
