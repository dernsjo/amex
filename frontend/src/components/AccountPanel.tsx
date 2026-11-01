import { useState } from "react";
import type { FormEvent } from "react";
import { createAccount, deleteAccount, errorMessage, updateAccount } from "../api";
import type { Account, AccountKind, Me } from "../api";
import { useDialogs } from "./ui";

interface Props {
    me: Me;
    accounts: Account[];
    onChanged: () => Promise<void>;
}

/** "" in a household select means "not shared". */
const toHouseholdId = (value: string) => (value ? Number(value) : null);

const KINDS: { value: AccountKind; label: string }[] = [
    { value: "debit", label: "Bank account" },
    { value: "credit", label: "Credit card" },
];
const kindName = (kind: AccountKind) => KINDS.find((k) => k.value === kind)?.label ?? kind;

const AccountPanel = ({ me, accounts, onChanged }: Props) => {
    const dialogs = useDialogs();
    const [name, setName] = useState("");
    const [shareWith, setShareWith] = useState("");
    const [kind, setKind] = useState<AccountKind>("debit");
    const [error, setError] = useState<string | null>(null);

    const householdName = (id: number | null) => me.households.find((h) => h.id === id)?.name ?? "Not shared";

    const run = async (action: () => Promise<unknown>) => {
        setError(null);
        try {
            await action();
            await onChanged();
        } catch (e) {
            setError(errorMessage(e));
        }
    };

    const handleCreate = (event: FormEvent) => {
        event.preventDefault();
        run(async () => {
            await createAccount(name, toHouseholdId(shareWith), kind);
            setName("");
            setKind("debit");
        });
    };

    const handleDelete = async (account: Account) => {
        if (await dialogs.confirm(`Delete ${account.name}?`, "All its imports and transactions are deleted too.", "Delete account"))
            run(() => deleteAccount(account.id));
    };

    const householdSelect = (value: string, onChange: (value: string) => void, label: string) => (
        <select className="select select-small" value={value} onChange={(e) => onChange(e.target.value)} aria-label={label}>
            <option value="">Not shared</option>
            {me.households.map((h) => (
                <option key={h.id} value={h.id}>
                    Shared with {h.name}
                </option>
            ))}
        </select>
    );

    return (
        <section className="block">
            <div className="block-head">
                <h2>Accounts</h2>
                <span className="small muted">
                    Sharing an account into a household splits its spending there. A bank account's spending is paid
                    already; a credit card's is split as a bill when you settle up.
                </span>
            </div>
            {error && (
                <p role="alert" className="alert">
                    {error}
                </p>
            )}
            {accounts.length > 0 && (
                <div className="table-wrap">
                    <table className="table table-stack">
                        <thead>
                            <tr>
                                <th>Account</th>
                                <th>Owner</th>
                                <th>Type</th>
                                <th>Sharing</th>
                                <th />
                            </tr>
                        </thead>
                        <tbody>
                            {accounts.map((a) => {
                                const mine = a.owner.user_id === me.id;
                                return (
                                    <tr key={a.id}>
                                        <td className="cell-desc">{a.name}</td>
                                        <td data-label="Owner">{mine ? "You" : a.owner.display_name}</td>
                                        <td data-label="Type">
                                            {mine ? (
                                                <select
                                                    className="select select-small"
                                                    value={a.kind}
                                                    onChange={(e) => run(() => updateAccount(a.id, { kind: e.target.value as AccountKind }))}
                                                    aria-label={`Type of ${a.name}`}
                                                >
                                                    {KINDS.map((k) => (
                                                        <option key={k.value} value={k.value}>
                                                            {k.label}
                                                        </option>
                                                    ))}
                                                </select>
                                            ) : (
                                                kindName(a.kind)
                                            )}
                                        </td>
                                        <td style={{ minWidth: "14rem" }}>
                                            {mine
                                                ? householdSelect(
                                                      String(a.household_id ?? ""),
                                                      (v) => run(() => updateAccount(a.id, { household_id: toHouseholdId(v) })),
                                                      `Sharing for ${a.name}`,
                                                  )
                                                : householdName(a.household_id)}
                                        </td>
                                        <td className="num">
                                            {mine && (
                                                <button className="btn btn-small" onClick={() => handleDelete(a)}>
                                                    Delete
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
            <form onSubmit={handleCreate} className="panel">
                <p className="lead">Add an account</p>
                <div className="row">
                    <label className="field grow">
                        <span>Name</span>
                        <input
                            className="input"
                            type="text"
                            placeholder="e.g. Amex Gold"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            required
                        />
                    </label>
                    <label className="field">
                        <span>Type</span>
                        <select className="select" value={kind} onChange={(e) => setKind(e.target.value as AccountKind)}>
                            {KINDS.map((k) => (
                                <option key={k.value} value={k.value}>
                                    {k.label}
                                </option>
                            ))}
                        </select>
                    </label>
                    {me.households.length > 0 && (
                        <label className="field grow">
                            <span>Sharing</span>
                            <select className="select" value={shareWith} onChange={(e) => setShareWith(e.target.value)}>
                                <option value="">Not shared</option>
                                {me.households.map((h) => (
                                    <option key={h.id} value={h.id}>
                                        Shared with {h.name}
                                    </option>
                                ))}
                            </select>
                        </label>
                    )}
                    <button type="submit" className="btn btn-ink">
                        Add account
                    </button>
                </div>
            </form>
        </section>
    );
};

export default AccountPanel;
