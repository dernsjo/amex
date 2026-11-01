import { useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../supabase";

interface Props {
    onDone: () => void;
    onCancel?: () => void;
}

/** Choose a password for the signed-in user: after a reset link, or to stop needing magic links. */
const SetPassword = ({ onDone, onCancel }: Props) => {
    const [password, setPassword] = useState("");
    const [repeat, setRepeat] = useState("");
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (event: FormEvent) => {
        event.preventDefault();
        if (password !== repeat) {
            setError("The passwords don't match");
            return;
        }
        const { error } = await supabase.auth.updateUser({ password });
        if (error) setError(error.message);
        else onDone();
    };

    return (
        <form onSubmit={handleSubmit} style={{ display: "inline-flex", flexDirection: "column", gap: 8 }}>
            <input
                type="password"
                placeholder="New password"
                autoComplete="new-password"
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
            />
            <input
                type="password"
                placeholder="Repeat it"
                autoComplete="new-password"
                value={repeat}
                onChange={(e) => setRepeat(e.target.value)}
                required
            />
            <span>
                <button type="submit">Save password</button>{" "}
                {onCancel && (
                    <button type="button" onClick={onCancel}>
                        Cancel
                    </button>
                )}
            </span>
            {error && <p role="alert">{error}</p>}
        </form>
    );
};

export default SetPassword;
