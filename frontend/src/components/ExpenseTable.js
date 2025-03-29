import React, { useState } from "react";
import { updatePaidBy, deleteExpense } from "../api";

function ExpenseTable({ expenses, paidByOptions, fetchExpenses }) {
    const [editingExpenseId, setEditingExpenseId] = useState(null);
    const [updatedPaidBy, setUpdatedPaidBy] = useState("");

    const startEditing = (expenseId, currentPaidBy) => {
        setEditingExpenseId(expenseId);
        setUpdatedPaidBy(currentPaidBy);
    };

    const handleUpdatePaidBy = async (expenseId) => {
        if (!updatedPaidBy) return;

        try {
            await updatePaidBy(expenseId, updatedPaidBy);
            setEditingExpenseId(null);
            fetchExpenses();  // Refresh the table
        } catch (error) {
            console.error("Error updating paid_by:", error);
        }
    };

    const handleDeleteExpense = async (expenseId) => {
        try {
            await deleteExpense(expenseId);
            fetchExpenses(); // Refresh the table after deletion
        } catch (error) {
            console.error("Error deleting expense:", error);
        }
    };

    return (
        <div>
            <h3>Expense Table</h3>
            <table border="1" style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                    <tr>
                        <th>Description</th>
                        <th>Amount</th>
                        <th>Paid By</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {expenses.map((expense) => (
                        <tr key={expense.id}>
                            <td>{expense.description}</td>
                            <td>{expense.amount}</td>
                            <td>
                                {editingExpenseId === expense.id ? (
                                    <>
                                        <select
                                            value={updatedPaidBy}
                                            onChange={(e) => setUpdatedPaidBy(e.target.value)}
                                        >
                                            {paidByOptions.map((option) => (
                                                <option key={option} value={option}>
                                                    {option}
                                                </option>
                                            ))}
                                        </select>
                                        <button onClick={() => handleUpdatePaidBy(expense.id)}>Save</button>
                                        <button onClick={() => setEditingExpenseId(null)}>Cancel</button>
                                    </>
                                ) : (
                                    <span onClick={() => startEditing(expense.id, expense.paid_by)}>
                                        {expense.paid_by}
                                    </span>
                                )}
                            </td>
                            <td>
                                <button onClick={() => handleDeleteExpense(expense.id)}>Delete</button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

export default ExpenseTable;