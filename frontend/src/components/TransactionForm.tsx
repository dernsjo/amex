import { useState } from "react";
import type { FormEvent } from "react";
import { createTransaction, errorMessage } from "../api";
import type { Account } from "../api";

interface Props {
    accounts: Account[]; // the user's own accounts
    categoriesFor: (account: Account | undefined) => string[];
    fetchTransactions: () => Promise<void>;
}

/** Add one transaction by hand, e.g. cash; folded away until needed. */
function TransactionForm({ accounts, categoriesFor, fetchTransactions }: Props) {
    const [open, setOpen] = useState(false);
    const [accountId, setAccountId] = useState<number | null>(null);
    const [description, setDescription] = useState("");
    const [amount, setAmount] = useState("");
    const [category, setCategory] = useState(""); // "" = categorize automatically
    const [error, setError] = useState<string | null>(null);

    const selected = accountId ?? accounts[0]?.id ?? null;
    const categories = categoriesFor(accounts.find((a) => a.id === selected));

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

    if (!open)
        return (
            <div>
                <button className="btn" onClick={() => setOpen(true)}>
                    Add a transaction by hand
                </button>
            </div>
        );

    return (
        <form onSubmit={handleAdd} className="panel rise">
            <div className="block-head">
                <p className="lead">Add a transaction</p>
                <button type="button" className="link small" onClick={() => setOpen(false)}>
                    Close
                </button>
            </div>
            <div className="row">
                <label className="field grow">
                    <span>Account</span>
                    <select className="select" value={selected ?? ""} onChange={(e) => setAccountId(Number(e.target.value))} required>
                        {accounts.map((a) => (
                            <option key={a.id} value={a.id}>
                                {a.name}
                            </option>
                        ))}
                    </select>
                </label>
                <label className="field grow">
                    <span>Description</span>
                    <input
                        className="input"
                        type="text"
                        placeholder="e.g. Market stall, cash"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        required
                    />
                </label>
                <label className="field" style={{ flex: "0 1 9rem" }}>
                    <span>Kronor</span>
                    <input
                        className="input"
                        type="number"
                        step="0.01"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        required
                    />
                </label>
                <label className="field grow">
                    <span>Category</span>
                    <select className="select" value={category} onChange={(e) => setCategory(e.target.value)}>
                        <option value="">Sort it for me</option>
                        {categories.map((option) => (
                            <option key={option} value={option}>
                                {option}
                            </option>
                        ))}
                    </select>
                </label>
                <button type="submit" className="btn btn-ink">
                    Add
                </button>
            </div>
            {error && (
                <p role="alert" className="alert">
                    {error}
                </p>
            )}
        </form>
    );
}

export default TransactionForm;
