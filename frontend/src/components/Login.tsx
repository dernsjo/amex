import { useState } from "react";
import type { FormEvent } from "react";
import { supabase } from "../supabase";

type Mode = "signIn" | "signUp" | "reset" | "link";

const SUBMIT: Record<Mode, string> = {
    signIn: "Sign in",
    signUp: "Create account",
    reset: "Email me a reset link",
    link: "Email me a sign-in link",
};

/** Sign in with Google, with email and password, or with a magic link. Every email comes back to this page. */
const Login = () => {
    const [mode, setMode] = useState<Mode>("signIn");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [message, setMessage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const switchTo = (next: Mode) => {
        setMode(next);
        setError(null);
        setMessage(null);
    };

    const handleGoogle = async () => {
        setError(null);
        const { error } = await supabase.auth.signInWithOAuth({
            provider: "google",
            options: { redirectTo: window.location.origin },
        });
        if (error) setError(error.message);
    };

    const handleSubmit = async (event: FormEvent) => {
        event.preventDefault();
        setError(null);
        const redirectTo = window.location.origin;
        switch (mode) {
            case "signIn": {
                const { error } = await supabase.auth.signInWithPassword({ email, password });
                if (error) setError(error.message);
                return;
            }
            case "signUp": {
                const { data, error } = await supabase.auth.signUp({
                    email,
                    password,
                    options: { emailRedirectTo: redirectTo },
                });
                if (error) setError(error.message);
                // Without a session the address must be confirmed first.
                else if (!data.session) setMessage(`Check ${email} to confirm your address, then sign in.`);
                return;
            }
            case "reset": {
                const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo });
                if (error) setError(error.message);
                else setMessage(`Check ${email} for a link to choose a new password.`);
                return;
            }
            case "link": {
                const { error } = await supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: redirectTo } });
                if (error) setError(error.message);
                else setMessage(`Check ${email} for a sign-in link.`);
                return;
            }
        }
    };

    const needsPassword = mode === "signIn" || mode === "signUp";

    return (
        <div style={{ maxWidth: 360, margin: "80px auto" }}>
            <h1>{mode === "signUp" ? "Create account" : mode === "reset" ? "Reset password" : "Sign in"}</h1>
            <button onClick={handleGoogle} style={{ width: "100%" }}>
                Continue with Google
            </button>
            <p>or</p>
            {message ? (
                <p role="status">{message}</p>
            ) : (
                <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <input
                        type="email"
                        placeholder="you@example.com"
                        autoComplete="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />
                    {needsPassword && (
                        <input
                            type="password"
                            placeholder="Password"
                            autoComplete={mode === "signUp" ? "new-password" : "current-password"}
                            minLength={mode === "signUp" ? 8 : undefined}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    )}
                    <button type="submit">{SUBMIT[mode]}</button>
                    {error && <p role="alert">{error}</p>}
                </form>
            )}
            <p style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center" }}>
                {mode !== "signIn" && <button onClick={() => switchTo("signIn")}>Sign in with password</button>}
                {mode !== "signUp" && <button onClick={() => switchTo("signUp")}>Create account</button>}
                {mode !== "reset" && <button onClick={() => switchTo("reset")}>Forgot password?</button>}
                {mode !== "link" && <button onClick={() => switchTo("link")}>Email me a link instead</button>}
            </p>
        </div>
    );
};

export default Login;
