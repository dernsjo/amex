import { useState } from "react";
import type { FormEvent } from "react";
import { createExpense, errorMessage } from "../api";

interface Props {
    paidByOptions: string[];
    categories: string[];
    fetchExpenses: () => Promise<void>;
}

function ExpenseForm({ paidByOptions, categories, fetchExpenses }: Props) {
    const [description, setDescription] = useState("");
    const [amount, setAmount] = useState("");
    const [paidBy, setPaidBy] = useState("Split");
    const [category, setCategory] = useState(""); // "" = categorize automatically
    const [error, setError] = useState<string | null>(null);

    const handleAddExpense = async (event: FormEvent) => {
        event.preventDefault();
        setError(null);
        try {
            // The server fills in today's date, and a category unless one is picked.
            await createExpense({
                description,
                amount: parseFloat(amount),
                paid_by: paidBy,
                ...(category && { category }),
            });
            setDescription("");
            setAmount("");
            setPaidBy("Split");
            setCategory("");
            await fetchExpenses();
        } catch (e) {
            setError(errorMessage(e));
        }
    };

    return (
        <div>
            <h2>Add Expense</h2>
            <form onSubmit={handleAddExpense}>
                <input
                    type="text"
                    placeholder="Description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    required
                />
                <input
                    type="number"
                    step="0.01"
                    placeholder="Amount"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    required
                />
                <select value={paidBy} onChange={(e) => setPaidBy(e.target.value)}>
                    {paidByOptions.map((option) => (
                        <option key={option} value={option}>
                            {option}
                        </option>
                    ))}
                </select>
                <select value={category} onChange={(e) => setCategory(e.target.value)}>
                    <option value="">Category: auto</option>
                    {categories.map((option) => (
                        <option key={option} value={option}>
                            {option}
                        </option>
                    ))}
                </select>
                <button type="submit">Add Expense</button>
                {error && <p role="alert">{error}</p>}
            </form>
        </div>
    );
}

export default ExpenseForm;
