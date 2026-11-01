import { useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../supabase";

/** Passwordless sign-in: Supabase emails a magic link that comes back to this page. */
const Login = () => {
    const [email, setEmail] = useState("");
    const [sent, setSent] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (event: FormEvent) => {
        event.preventDefault();
        setError(null);
        const { error } = await supabase.auth.signInWithOtp({
            email,
            options: { emailRedirectTo: window.location.origin },
        });
        if (error) setError(error.message);
        else setSent(true);
    };

    return (
        <div style={{ maxWidth: 360, margin: "80px auto" }}>
            <h1>Sign in</h1>
            {sent ? (
                <p role="status">Check {email} for a sign-in link.</p>
            ) : (
                <form onSubmit={handleSubmit}>
                    <input
                        type="email"
                        placeholder="you@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />
                    <button type="submit">Email me a sign-in link</button>
                    {error && <p role="alert">{error}</p>}
                </form>
            )}
        </div>
    );
};

export default Login;
