import { useState } from "react";
import { ALLOCATIONS, createRule, deleteTransaction, errorMessage, kr, suggestPattern, updateTransaction } from "../api";
import type { Account, Allocation, Transaction, TransactionChanges } from "../api";

interface Props {
    me: number;
    transactions: Transaction[];
    accounts: Account[];
    categoriesFor: (account: Account | undefined) => string[];
    fetchTransactions: () => Promise<void>;
}

interface Draft {
    id: number;
    allocation: Allocation;
    member_id: number | null;
    category: string;
}

interface Option {
    value: string;
    label: string;
}

/** The scope's categories, plus the current one if it isn't among them (e.g. from before the account was shared). */
const categoryOptions = (names: string[], current: string): Option[] =>
    (names.includes(current) ? names : [current, ...names]).map((c) => ({ value: c, label: c }));

const Select = ({ value, options, onChange }: { value: string; options: Option[]; onChange: (v: string) => void }) => (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((option) => (
            <option key={option.value} value={option.value}>
                {option.label}
            </option>
        ))}
    </select>
);

function TransactionTable({ me, transactions, accounts, categoriesFor, fetchTransactions }: Props) {
    // The row being edited; clicking its Category or Allocation cell starts editing.
    const [draft, setDraft] = useState<Draft | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [message, setMessage] = useState<string | null>(null);

    const accountById = new Map(accounts.map((a) => [a.id, a]));
    const personName = (t: Transaction) =>
        accountById.get(t.account_id)?.members.find((m) => m.user_id === t.member_id)?.display_name ?? "?";

    const startEditing = (t: Transaction) => {
        setDraft({ id: t.id, allocation: t.allocation, member_id: t.member_id, category: t.category ?? "Other" });
    };

    /** After a correction, offer to do the same for similar transactions from now on. */
    const offerRule = async (t: Transaction, category: string) => {
        const pattern = window
            .prompt(
                `Always put transactions containing this text in ${category}? Edit the text, or cancel.`,
                suggestPattern(t.description),
            )
            ?.trim();
        if (!pattern) return;
        const result = await createRule(accountById.get(t.account_id)?.household_id ?? null, pattern, category);
        setMessage(`Rule added: "${result.rule.pattern}" → ${category}. ${result.recategorized} other transaction(s) moved.`);
    };

    const handleSave = async (t: Transaction) => {
        if (!draft) return;
        setError(null);
        setMessage(null);
        try {
            const changes: TransactionChanges = {
                ...(draft.allocation !== t.allocation && { allocation: draft.allocation }),
                ...(draft.allocation === "personal" &&
                    draft.member_id !== t.member_id && { member_id: draft.member_id }),
                ...(draft.category !== t.category && { category: draft.category }),
            };
            if (Object.keys(changes).length > 0) {
                await updateTransaction(t.id, changes);
                setDraft(null);
                if (changes.category) await offerRule(t, changes.category);
                await fetchTransactions();
            }
            setDraft(null);
        } catch (e) {
            setError(errorMessage(e));
        }
    };

    const handleDelete = async (transactionId: number) => {
        setError(null);
        try {
            await deleteTransaction(transactionId);
            await fetchTransactions();
        } catch (e) {
            setError(errorMessage(e));
        }
    };

    return (
        <div>
            <h3>Transactions</h3>
            <p>Click a Category or Allocation value to edit it.</p>
            {error && <p role="alert">{error}</p>}
            {message && <p role="status">{message}</p>}
            <table border={1} style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Description</th>
                        <th>Account</th>
                        <th>Category</th>
                        <th>Amount</th>
                        <th>Allocation</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {transactions.map((t) => {
                        const editing = draft?.id === t.id ? draft : null;
                        const account = accountById.get(t.account_id);
                        const members = account?.members ?? [];
                        return (
                            <tr key={t.id}>
                                <td>{t.booked_on}</td>
                                <td>{t.description}</td>
                                <td>{account?.name}</td>
                                <td>
                                    {editing ? (
                                        <Select
                                            value={editing.category}
                                            options={categoryOptions(categoriesFor(account), editing.category)}
                                            onChange={(category) => setDraft({ ...editing, category })}
                                        />
                                    ) : (
                                        <span style={{ cursor: "pointer" }} onClick={() => startEditing(t)}>
                                            {t.category ?? "—"}
                                        </span>
                                    )}
                                </td>
                                <td>{kr(t.amount_minor, t.currency)}</td>
                                <td>
                                    {editing ? (
                                        <>
                                            <Select
                                                value={editing.allocation}
                                                options={ALLOCATIONS.map((a) => ({ value: a, label: a }))}
                                                onChange={(v) =>
                                                    setDraft({
                                                        ...editing,
                                                        allocation: v as Allocation,
                                                        member_id: editing.member_id ?? account?.owner.user_id ?? null,
                                                    })
                                                }
                                            />
                                            {editing.allocation === "personal" && members.length > 1 && (
                                                <Select
                                                    value={String(editing.member_id ?? "")}
                                                    options={members.map((m) => ({
                                                        value: String(m.user_id),
                                                        label: m.display_name,
                                                    }))}
                                                    onChange={(v) => setDraft({ ...editing, member_id: Number(v) })}
                                                />
                                            )}
                                        </>
                                    ) : (
                                        <span style={{ cursor: "pointer" }} onClick={() => startEditing(t)}>
                                            {t.allocation === "personal" ? `personal: ${personName(t)}` : t.allocation}
                                        </span>
                                    )}
                                </td>
                                <td>
                                    {editing ? (
                                        <>
                                            <button onClick={() => handleSave(t)}>Save</button>
                                            <button onClick={() => setDraft(null)}>Cancel</button>
                                        </>
                                    ) : (
                                        account?.owner.user_id === me && (
                                            <button onClick={() => handleDelete(t.id)}>Delete</button>
                                        )
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

export default TransactionTable;
