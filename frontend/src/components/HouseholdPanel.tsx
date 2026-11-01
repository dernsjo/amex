import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { addMember, createHousehold, errorMessage, getHousehold, removeMember, updateMember } from "../api";
import type { Household, Me } from "../api";
import { ShareBar, memberColor, useDialogs } from "./ui";

interface Props {
    me: Me;
    householdId: number | null; // null: no household selected, offer to create one
    onChanged: (selectHouseholdId?: number | null) => Promise<void>;
}

const HouseholdPanel = ({ me, householdId, onChanged }: Props) => {
    const dialogs = useDialogs();
    const [household, setHousehold] = useState<Household | null>(null);
    // Weights as typed, before they're saved: the split bar follows them live.
    const [weights, setWeights] = useState<Record<number, string>>({});
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

    useEffect(() => {
        setWeights(Object.fromEntries((household?.members ?? []).map((m) => [m.user_id, String(m.split_weight)])));
    }, [household]);

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
        const member = household?.members.find((m) => m.user_id === userId);
        if (!household || Number.isNaN(split_weight) || member?.split_weight === split_weight) return;
        run(async () => setHousehold(await updateMember(household.id, userId, { split_weight })));
    };

    const handleRemove = async (userId: number, displayName: string) => {
        if (!household) return;
        const leaving = userId === me.id;
        const ok = await dialogs.confirm(
            leaving ? `Leave ${household.name}?` : `Remove ${displayName}?`,
            leaving
                ? "Your accounts stop being shared with it."
                : `${displayName}'s accounts stop being shared with ${household.name}.`,
            leaving ? "Leave" : "Remove",
        );
        if (!ok) return;
        run(async () => {
            await removeMember(household.id, userId);
            if (leaving) await onChanged(null);
            else await fetchHousehold();
        });
    };

    if (!household) {
        return (
            <section className="tile tile-3 rise" style={{ minHeight: "24rem", alignContent: "end" }}>
                <h2 className="head">Share with a household</h2>
                <p>
                    Optional. A household shares the accounts you choose and splits their spending between its members,
                    50/50 or by any weights you set.
                    {me.households.length > 0 && " To manage one you're in, choose it under Showing."}
                </p>
                <form onSubmit={handleCreate} className="row" style={{ maxWidth: "36rem" }}>
                    <label className="field grow">
                        <span style={{ color: "var(--ink)" }}>Household name</span>
                        <input
                            className="input"
                            type="text"
                            placeholder="e.g. Home"
                            value={newName}
                            onChange={(e) => setNewName(e.target.value)}
                            required
                        />
                    </label>
                    <button type="submit" className="btn btn-ink">
                        Create household
                    </button>
                </form>
                {error && (
                    <p role="alert" className="alert">
                        {error}
                    </p>
                )}
            </section>
        );
    }

    const isOwner = household.members.some((m) => m.user_id === me.id && m.role === "owner");
    const typed = household.members.map((m) => Math.max(0, parseInt(weights[m.user_id] ?? "", 10) || 0));
    const totalWeight = typed.reduce((sum, w) => sum + w, 0);
    const pct = (w: number) => (totalWeight > 0 ? Math.round((100 * w) / totalWeight) : 0);

    return (
        <section className="block">
            <div className="block-head">
                <h2>{household.name}</h2>
                <span className="small muted">
                    {household.members.length} member{household.members.length === 1 ? "" : "s"}
                </span>
            </div>
            {error && (
                <p role="alert" className="alert">
                    {error}
                </p>
            )}

            <div className="weights">
                <p className="lead">
                    Shared spending splits {typed.map((w) => `${pct(w)}`).join(" / ")}
                </p>
                <ShareBar
                    parts={household.members.map((m, i) => ({
                        value: typed[i],
                        color: memberColor(i),
                        label: `${m.display_name} ${pct(typed[i])}%`,
                    }))}
                />
            </div>

            <div className="table-wrap">
                <table className="table table-stack">
                    <thead>
                        <tr>
                            <th>Member</th>
                            <th>Email</th>
                            <th>Role</th>
                            <th>Weight</th>
                            <th />
                        </tr>
                    </thead>
                    <tbody>
                        {household.members.map((m, i) => (
                            <tr key={m.user_id}>
                                <td className="cell-desc">
                                    <span className="swatch" style={{ background: memberColor(i) }} />
                                    {m.display_name}
                                    {m.pending && <span className="small muted"> · hasn't signed in yet</span>}
                                </td>
                                <td>{m.email}</td>
                                <td>{m.role === "owner" ? "Owner" : "Member"}</td>
                                <td style={{ whiteSpace: "nowrap" }}>
                                    {isOwner ? (
                                        <input
                                            className="input input-small weight-input"
                                            type="number"
                                            min={0}
                                            value={weights[m.user_id] ?? ""}
                                            onChange={(e) => setWeights({ ...weights, [m.user_id]: e.target.value })}
                                            onBlur={(e) => handleWeight(m.user_id, e.target.value)}
                                            aria-label={`Split weight for ${m.display_name}`}
                                        />
                                    ) : (
                                        m.split_weight
                                    )}{" "}
                                    <span className="muted">{pct(typed[i])}%</span>
                                </td>
                                <td className="num">
                                    {m.user_id === me.id ? (
                                        <button className="btn btn-small" onClick={() => handleRemove(m.user_id, m.display_name)}>
                                            Leave
                                        </button>
                                    ) : (
                                        isOwner && (
                                            <button className="btn btn-small" onClick={() => handleRemove(m.user_id, m.display_name)}>
                                                Remove
                                            </button>
                                        )
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            {isOwner && <p className="small muted">Weights are relative: 1 and 1 is 50/50, 3 and 2 is 60/40.</p>}

            {isOwner && (
                <form onSubmit={handleAddMember} className="panel">
                    <p className="lead">Add someone</p>
                    <div className="row">
                        <label className="field grow">
                            <span>Email</span>
                            <input
                                className="input"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                            />
                        </label>
                        <label className="field grow">
                            <span>Name, if they haven't signed in yet</span>
                            <input className="input" type="text" value={name} onChange={(e) => setName(e.target.value)} />
                        </label>
                        <button type="submit" className="btn btn-ink">
                            Add member
                        </button>
                    </div>
                    <p className="small muted">
                        You can split with them right away; they join when they first sign in with this email.
                    </p>
                </form>
            )}
        </section>
    );
};

export default HouseholdPanel;
