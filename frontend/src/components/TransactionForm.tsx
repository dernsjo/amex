import { useState } from "react";
import type { FormEvent } from "react";
import { createTransaction, errorMessage } from "../api";
import type { Account } from "../api";
import AccountSelect from "./AccountSelect";

interface Props {
    accounts: Account[]; // the user's own accounts
    categories: string[];
    fetchTransactions: () => Promise<void>;
}

function TransactionForm({ accounts, categories, fetchTransactions }: Props) {
    const [accountId, setAccountId] = useState<number | null>(null);
    const [description, setDescription] = useState("");
    const [amount, setAmount] = useState("");
    const [category, setCategory] = useState(""); // "" = categorize automatically
    const [error, setError] = useState<string | null>(null);

    const selected = accountId ?? accounts[0]?.id ?? null;

    const handleAdd = async (event: FormEvent) => {
        event.preventDefault();
        if (selected === null) return;
        setError(null);
        try {
            // The server fills in today's date, an allocation, and a category unless one is picked.
            await createTransaction(selected, {
                description,
                amount: parseFloat(amount),
                ...(category && { category }),
            });
            setDescription("");
            setAmount("");
            setCategory("");
            await fetchTransactions();
        } catch (e) {
            setError(errorMessage(e));
        }
    };

    if (accounts.length === 0) return null;

    return (
        <div>
            <h2>Add Transaction</h2>
            <form onSubmit={handleAdd}>
                <AccountSelect accounts={accounts} value={selected} onChange={setAccountId} />
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
                <select value={category} onChange={(e) => setCategory(e.target.value)}>
                    <option value="">Category: auto</option>
                    {categories.map((option) => (
                        <option key={option} value={option}>
                            {option}
                        </option>
                    ))}
                </select>
                <button type="submit">Add Transaction</button>
                {error && <p role="alert">{error}</p>}
            </form>
        </div>
    );
}

export default TransactionForm;
