import { useState } from "react";
import type { FormEvent } from "react";
import { createAccount, deleteAccount, errorMessage, updateAccount } from "../api";
import type { Account, Me } from "../api";

interface Props {
    me: Me;
    accounts: Account[];
    onChanged: () => Promise<void>;
}

/** "" in a household select means "not shared". */
const toHouseholdId = (value: string) => (value ? Number(value) : null);

const AccountPanel = ({ me, accounts, onChanged }: Props) => {
    const [name, setName] = useState("");
    const [shareWith, setShareWith] = useState("");
    const [error, setError] = useState<string | null>(null);

    const householdName = (id: number | null) => me.households.find((h) => h.id === id)?.name ?? "—";

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
            await createAccount(name, toHouseholdId(shareWith));
            setName("");
        });
    };

    const handleDelete = (account: Account) => {
        if (window.confirm(`Delete ${account.name} and all its transactions?`)) run(() => deleteAccount(account.id));
    };

    const householdSelect = (value: string, onChange: (value: string) => void) => (
        <select value={value} onChange={(e) => onChange(e.target.value)}>
            <option value="">Not shared</option>
            {me.households.map((h) => (
                <option key={h.id} value={h.id}>
                    Shared with {h.name}
                </option>
            ))}
        </select>
    );

    return (
        <div>
            <h2>Accounts</h2>
            {accounts.length > 0 && (
                <table border={1} style={{ margin: "0 auto", borderCollapse: "collapse" }}>
                    <thead>
                        <tr>
                            <th>Account</th>
                            <th>Owner</th>
                            <th>Sharing</th>
                            <th />
                        </tr>
                    </thead>
                    <tbody>
                        {accounts.map((a) => {
                            const mine = a.owner.user_id === me.id;
                            return (
                                <tr key={a.id}>
                                    <td>{a.name}</td>
                                    <td>{mine ? "You" : a.owner.display_name}</td>
                                    <td>
                                        {mine
                                            ? householdSelect(String(a.household_id ?? ""), (v) =>
                                                  run(() => updateAccount(a.id, { household_id: toHouseholdId(v) })),
                                              )
                                            : householdName(a.household_id)}
                                    </td>
                                    <td>{mine && <button onClick={() => handleDelete(a)}>Delete</button>}</td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            )}
            <form onSubmit={handleCreate}>
                <input
                    type="text"
                    placeholder="New account, e.g. Amex"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                />
                {me.households.length > 0 && householdSelect(shareWith, setShareWith)}
                <button type="submit">Add account</button>
            </form>
            {error && <p role="alert">{error}</p>}
        </div>
    );
};

export default AccountPanel;
