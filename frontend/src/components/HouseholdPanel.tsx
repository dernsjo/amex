import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { addMember, createHousehold, errorMessage, getHousehold, removeMember, updateMember } from "../api";
import type { Household, Me } from "../api";

interface Props {
    me: Me;
    householdId: number | null; // null: no household selected, offer to create one
    onChanged: (selectHouseholdId?: number | null) => Promise<void>;
}

const HouseholdPanel = ({ me, householdId, onChanged }: Props) => {
    const [household, setHousehold] = useState<Household | null>(null);
    const [newName, setNewName] = useState("");
    const [email, setEmail] = useState("");
    const [name, setName] = useState("");
    const [error, setError] = useState<string | null>(null);

    const fetchHousehold = useCallback(async () => {
        setHousehold(householdId ? await getHousehold(householdId) : null);
    }, [householdId]);

    useEffect(() => {
        setError(null);
        fetchHousehold().catch((e) => setError(errorMessage(e)));
    }, [fetchHousehold]);

    const run = async (action: () => Promise<unknown>) => {
        setError(null);
        try {
            await action();
        } catch (e) {
            setError(errorMessage(e));
        }
    };

    const handleCreate = (event: FormEvent) => {
        event.preventDefault();
        run(async () => {
            const created = await createHousehold(newName);
            setNewName("");
            await onChanged(created.id);
        });
    };

    const handleAddMember = (event: FormEvent) => {
        event.preventDefault();
        if (!household) return;
        run(async () => {
            setHousehold(await addMember(household.id, email, name.trim()));
            setEmail("");
            setName("");
        });
    };

    const handleWeight = (userId: number, value: string) => {
        const split_weight = parseInt(value, 10);
        if (!household || Number.isNaN(split_weight)) return;
        run(async () => setHousehold(await updateMember(household.id, userId, { split_weight })));
    };

    const handleRemove = (userId: number) => {
        if (!household) return;
        run(async () => {
            await removeMember(household.id, userId);
            if (userId === me.id) await onChanged(null);
            else await fetchHousehold();
        });
    };

    if (!household) {
        return (
            <div>
                <h2>Share with a household</h2>
                <p>Optional: create a household to share accounts and split costs with others.</p>
                <form onSubmit={handleCreate}>
                    <input
                        type="text"
                        placeholder="Household name"
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                        required
                    />
                    <button type="submit">Create household</button>
                </form>
                {error && <p role="alert">{error}</p>}
            </div>
        );
    }

    const isOwner = household.members.some((m) => m.user_id === me.id && m.role === "owner");
    const totalWeight = household.members.reduce((sum, m) => sum + m.split_weight, 0);

    return (
        <div>
            <h2>{household.name}</h2>
            <table border={1} style={{ margin: "0 auto", borderCollapse: "collapse" }}>
                <thead>
                    <tr>
                        <th>Member</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Split weight</th>
                        <th />
                    </tr>
                </thead>
                <tbody>
                    {household.members.map((m) => (
                        <tr key={m.user_id}>
                            <td>
                                {m.display_name}
                                {m.pending && <em> (hasn't signed in yet)</em>}
                            </td>
                            <td>{m.email}</td>
                            <td>{m.role}</td>
                            <td>
                                {isOwner ? (
                                    <input
                                        type="number"
                                        min={0}
                                        defaultValue={m.split_weight}
                                        onBlur={(e) => handleWeight(m.user_id, e.target.value)}
                                        style={{ width: 60 }}
                                    />
                                ) : (
                                    m.split_weight
                                )}{" "}
                                {totalWeight > 0 && `(${Math.round((100 * m.split_weight) / totalWeight)}%)`}
                            </td>
                            <td>
                                {m.user_id === me.id ? (
                                    <button onClick={() => handleRemove(m.user_id)}>Leave</button>
                                ) : (
                                    isOwner && <button onClick={() => handleRemove(m.user_id)}>Remove</button>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
            {isOwner && (
                <form onSubmit={handleAddMember}>
                    <input
                        type="email"
                        placeholder="Email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />
                    <input
                        type="text"
                        placeholder="Name (if they haven't signed in yet)"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                    />
                    <button type="submit">Add member</button>
                    <p style={{ fontSize: "0.85em" }}>
                        Someone who hasn't signed in yet can be split with right away; they join when they first
                        sign in with this email.
                    </p>
                </form>
            )}
            {error && <p role="alert">{error}</p>}
        </div>
    );
};

export default HouseholdPanel;
