import React, { useState } from "react";
import { createExpense } from "../api";

function ExpenseForm({ paidByOptions, fetchExpenses }) {
    const [description, setDescription] = useState("");
    const [amount, setAmount] = useState("");
    const [paidBy, setPaidBy] = useState("Split");

    const handleAddExpense = async (event) => {
        event.preventDefault();
        await createExpense({
            description,
            amount: parseFloat(amount),
            paid_by: paidBy,
            date: new Date().toISOString(),
        });

        setDescription("");
        setAmount("");
        setPaidBy("Split");
        fetchExpenses();
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
                <button type="submit">Add Expense</button>
            </form>
        </div>
    );
}

export default ExpenseForm;
