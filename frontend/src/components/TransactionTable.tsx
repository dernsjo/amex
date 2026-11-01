import { Fragment, useState } from "react";
import type { FormEvent } from "react";
import { ALLOCATIONS, createRule, dayName, deleteTransaction, errorMessage, kr, suggestPattern, updateTransaction } from "../api";
import type { Account, Allocation, Transaction, TransactionChanges } from "../api";
import { Segmented } from "./ui";

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

/** After a correction: offer to do the same for similar transactions from now on. */
interface RuleOffer {
    householdId: number | null;
    pattern: string;
    category: string;
}

const ALLOCATION_LABEL: Record<Allocation, string> = {
    shared: "Shared",
    personal: "Personal",
    outlay: "Outlay",
    excluded: "Excluded",
};

const ALLOCATION_HINT: Record<Allocation, string> = {
    shared: "Split between the household by its weights.",
    personal: "Belongs to one person.",
    outlay: "Paid on someone's behalf; reported separately.",
    excluded: "Not spending: transfers, refunds, payments to the card.",
};

/** The scope's categories, plus the current one if it isn't among them (e.g. from before the account was shared). */
const categoryOptions = (names: string[], current: string) => (names.includes(current) ? names : [current, ...names]);

function TransactionTable({ me, transactions, accounts, categoriesFor, fetchTransactions }: Props) {
    // The row being edited; choosing a row starts editing it.
    const [draft, setDraft] = useState<Draft | null>(null);
    const [offer, setOffer] = useState<RuleOffer | null>(null);
    const [query, setQuery] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [message, setMessage] = useState<string | null>(null);

    const accountById = new Map(accounts.map((a) => [a.id, a]));
    const personName = (t: Transaction) =>
        accountById.get(t.account_id)?.members.find((m) => m.user_id === t.member_id)?.display_name ?? "?";

    const needle = query.trim().toLowerCase();
    const shown = needle
        ? transactions.filter((t) =>
              [t.description, t.category ?? "", accountById.get(t.account_id)?.name ?? ""].some((s) =>
                  s.toLowerCase().includes(needle),
              ),
          )
        : transactions;

    const startEditing = (t: Transaction) => {
        if (draft?.id === t.id) return;
        setDraft({ id: t.id, allocation: t.allocation, member_id: t.member_id, category: t.category ?? "Other" });
    };

    const handleSave = async (t: Transaction) => {
        if (!draft) return;
        setError(null);
        setMessage(null);
        try {
            const changes: TransactionChanges = {
                ...(draft.allocation !== t.allocation && { allocation: draft.allocation }),
                ...(draft.allocation === "personal" && draft.member_id !== t.member_id && { member_id: draft.member_id }),
                ...(draft.category !== t.category && { category: draft.category }),
            };
            if (Object.keys(changes).length > 0) {
                await updateTransaction(t.id, changes);
                if (changes.category)
                    setOffer({
                        householdId: accountById.get(t.account_id)?.household_id ?? null,
                        pattern: suggestPattern(t.description),
                        category: changes.category,
                    });
                await fetchTransactions();
            }
            setDraft(null);
        } catch (e) {
            setError(errorMessage(e));
        }
    };

    const handleRule = async (event: FormEvent) => {
        event.preventDefault();
        if (!offer?.pattern.trim()) return;
        try {
            const result = await createRule(offer.householdId, offer.pattern.trim(), offer.category);
            setOffer(null);
            setMessage(`Rule added: "${result.rule.pattern}" goes to ${offer.category}. ${result.recategorized} other transaction(s) moved.`);
            await fetchTransactions();
        } catch (e) {
            setError(errorMessage(e));
        }
    };

    const handleDelete = async (transactionId: number) => {
        setError(null);
        try {
            await deleteTransaction(transactionId);
            setDraft(null);
            await fetchTransactions();
        } catch (e) {
            setError(errorMessage(e));
        }
    };

    return (
        <section className="block">
            <div className="toolbar">
                <input
                    className="input"
                    type="search"
                    placeholder="Search descriptions, categories, accounts"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    aria-label="Search transactions"
                />
                <span className="small muted">
                    {shown.length} of {transactions.length}
                </span>
            </div>

            {error && (
                <p role="alert" className="alert">
                    {error}
                </p>
            )}
            {message && (
                <p role="status" className="status">
                    {message}
                </p>
            )}
            {offer && (
                <form className="offer rise" onSubmit={handleRule}>
                    <p style={{ fontWeight: 500 }}>Always put transactions like this in {offer.category}?</p>
                    <div className="row">
                        <label className="field grow">
                            <span style={{ color: "var(--ink)" }}>When the description contains</span>
                            <input
                                className="input"
                                value={offer.pattern}
                                onChange={(e) => setOffer({ ...offer, pattern: e.target.value })}
                                minLength={2}
                                required
                            />
                        </label>
                        <div className="edit-actions">
                            <button type="submit" className="btn btn-ink">
                                Make it a rule
                            </button>
                            <button type="button" className="btn" style={{ background: "var(--bg)" }} onClick={() => setOffer(null)}>
                                Just this once
                            </button>
                        </div>
                    </div>
                </form>
            )}

            {transactions.length === 0 ? (
                <div className="empty">
                    <p className="lead">No transactions yet.</p>
                    <p>Import a statement, or add one by hand above.</p>
                </div>
            ) : (
                <div className="table-wrap">
                    <table className="table table-click table-txn">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Description</th>
                                <th>Category</th>
                                <th>Split</th>
                                <th>Account</th>
                                <th className="num">Amount</th>
                            </tr>
                        </thead>
                        <tbody>
                            {shown.map((t) => {
                                const editing = draft?.id === t.id ? draft : null;
                                const account = accountById.get(t.account_id);
                                const members = account?.members ?? [];
                                return (
                                    <Fragment key={t.id}>
                                        <tr
                                            className={editing ? "editing" : undefined}
                                            onClick={() => startEditing(t)}
                                            tabIndex={0}
                                            onKeyDown={(e) => {
                                                if (e.key === "Enter" && !editing) startEditing(t);
                                            }}
                                            aria-expanded={!!editing}
                                        >
                                            <td className="cell-date">{dayName(t.booked_on)}</td>
                                            <td className="cell-desc">{t.description}</td>
                                            <td>{t.category ?? "Uncategorized"}</td>
                                            <td>
                                                <span className={`tag tag-${t.allocation}`}>
                                                    {t.allocation === "personal" ? personName(t) : ALLOCATION_LABEL[t.allocation]}
                                                </span>
                                            </td>
                                            <td className="cell-account">{account?.name}</td>
                                            <td className={`num${t.amount_minor < 0 ? " amount-neg" : ""}`} style={{ fontWeight: 600 }}>
                                                {kr(t.amount_minor, t.currency)}
                                            </td>
                                        </tr>
                                        {editing && (
                                            <tr className="edit-panel">
                                                <td colSpan={6}>
                                                    <div className="edit-grid">
                                                        <label className="field">
                                                            <span>Category</span>
                                                            <select
                                                                className="select"
                                                                value={editing.category}
                                                                onChange={(e) => setDraft({ ...editing, category: e.target.value })}
                                                            >
                                                                {categoryOptions(categoriesFor(account), editing.category).map((c) => (
                                                                    <option key={c} value={c}>
                                                                        {c}
                                                                    </option>
                                                                ))}
                                                            </select>
                                                        </label>
                                                        <div className="field">
                                                            <span>How it's split</span>
                                                            <Segmented
                                                                label="Allocation"
                                                                value={editing.allocation}
                                                                options={ALLOCATIONS.map((a) => ({ value: a, label: ALLOCATION_LABEL[a] }))}
                                                                onChange={(allocation) =>
                                                                    setDraft({
                                                                        ...editing,
                                                                        allocation,
                                                                        member_id: editing.member_id ?? account?.owner.user_id ?? null,
                                                                    })
                                                                }
                                                            />
                                                            <span style={{ fontWeight: 400 }}>{ALLOCATION_HINT[editing.allocation]}</span>
                                                        </div>
                                                        <div className="edit-actions">
                                                            <button className="btn btn-ink btn-small" onClick={() => handleSave(t)}>
                                                                Save
                                                            </button>
                                                            <button className="btn btn-small" style={{ background: "var(--bg)" }} onClick={() => setDraft(null)}>
                                                                Cancel
                                                            </button>
                                                            {account?.owner.user_id === me && (
                                                                <button
                                                                    className="btn btn-small"
                                                                    style={{ background: "var(--bg)" }}
                                                                    onClick={() => handleDelete(t.id)}
                                                                >
                                                                    Delete
                                                                </button>
                                                            )}
                                                        </div>
                                                        {editing.allocation === "personal" && members.length > 1 && (
                                                            <div className="field">
                                                                <span>Whose is it?</span>
                                                                <Segmented
                                                                    label="Whose"
                                                                    value={String(editing.member_id ?? "")}
                                                                    options={members.map((m) => ({
                                                                        value: String(m.user_id),
                                                                        label: m.display_name,
                                                                    }))}
                                                                    onChange={(v) => setDraft({ ...editing, member_id: Number(v) })}
                                                                />
                                                            </div>
                                                        )}
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </Fragment>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </section>
    );
}

export default TransactionTable;
