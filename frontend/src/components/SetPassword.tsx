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
        <form onSubmit={handleSubmit} style={{ display: "grid", gap: "0.85rem", maxWidth: "26rem" }}>
            <label className="field">
                <span>New password, at least 8 characters</span>
                <input
                    className="input"
                    type="password"
                    autoComplete="new-password"
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                />
            </label>
            <label className="field">
                <span>Repeat it</span>
                <input
                    className="input"
                    type="password"
                    autoComplete="new-password"
                    value={repeat}
                    onChange={(e) => setRepeat(e.target.value)}
                    required
                />
            </label>
            <div className="edit-actions">
                <button type="submit" className="btn btn-primary">
                    Save password
                </button>
                {onCancel && (
                    <button type="button" className="btn" onClick={onCancel}>
                        Cancel
                    </button>
                )}
            </div>
            {error && (
                <p role="alert" className="alert">
                    {error}
                </p>
            )}
        </form>
    );
};

export default SetPassword;
