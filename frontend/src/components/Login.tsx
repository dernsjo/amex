import { useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { kr } from "../api";
import { supabase } from "../supabase";
import { ShareBar, Wordmark } from "./ui";

type Mode = "signIn" | "signUp" | "reset" | "link";

const TITLE: Record<Mode, string> = {
    signIn: "Sign in",
    signUp: "Create your account",
    reset: "Reset your password",
    link: "Sign in by email",
};

const SUBMIT: Record<Mode, string> = {
    signIn: "Sign in",
    signUp: "Create account",
    reset: "Email me a reset link",
    link: "Email me a sign-in link",
};

const BILL_MINOR = 124_000; // a sample bill, in öre

/**
 * The brand side of the sign-in screen. The live thing: drag the split of one
 * bill and watch the mark itself, and who owes whom, follow to the öre.
 */
const BrandPanel = () => {
    const [yours, setYours] = useState(50); // percent of the bill that is yours
    const theirs = 100 - yours;
    const owed = Math.round((BILL_MINOR * theirs) / 100);
    return (
        <aside className="auth-brand" aria-label="About Leva">
            <div className="auth-motif" aria-hidden="true">
                <span className="a" style={{ flexGrow: yours, flexBasis: 0 }} />
                <span className="b" style={{ flexGrow: theirs, flexBasis: 0 }} />
            </div>
            <div className="auth-brand-copy">
                <p className="head">Money, for the way you live.</p>
                <p>
                    Import your bank statements and see where your money goes, for you and your household: every
                    purchase sorted, budgeted and shared fairly, down to the öre.
                </p>
            </div>
            <div className="demo" data-ui>
                <div className="demo-line">
                    <span>Dinner, paid by you</span>
                    <span className="nums">{kr(BILL_MINOR)}</span>
                </div>
                <ShareBar
                    parts={[
                        { value: yours, className: "over", title: `You ${yours}%` },
                        { value: theirs, className: "spent", title: `Sam ${theirs}%` },
                    ]}
                />
                <label className="field">
                    <span>
                        You {yours}% · Sam {theirs}%
                    </span>
                    <input
                        className="range"
                        type="range"
                        min={0}
                        max={100}
                        step={5}
                        value={yours}
                        onChange={(e) => setYours(Number(e.target.value))}
                        aria-label="Your share of the bill, in percent"
                    />
                </label>
                <p className="demo-result" aria-live="polite">
                    {owed === 0 ? "You're even." : <>Sam owes you {kr(owed)}</>}
                </p>
            </div>
        </aside>
    );
};

/** The two-sided frame shared by sign-in and choosing a new password. */
export const AuthLayout = ({ children }: { children: ReactNode }) => (
    <div className="auth">
        <main className="auth-form">
            <Wordmark />
            <div className="auth-form-body rise">{children}</div>
            <p className="auth-foot">Leva reads your statements. It never moves money.</p>
        </main>
        <BrandPanel />
    </div>
);

/** Sign in with Google, with email and password, or with a magic link. Every email comes back to this page. */
const Login = () => {
    const [mode, setMode] = useState<Mode>("signIn");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [message, setMessage] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [busy, setBusy] = useState(false);

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
        setBusy(true);
        try {
            await submit();
        } finally {
            setBusy(false);
        }
    };

    const submit = async () => {
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
        <AuthLayout>
            <h1 className="head">{TITLE[mode]}</h1>
            {message ? (
                <p role="status" className="status">
                    {message}
                </p>
            ) : (
                <>
                    <button type="button" className="btn btn-ink btn-wide" onClick={handleGoogle}>
                        Continue with Google
                    </button>
                    <p className="or">or with your email</p>
                    <form onSubmit={handleSubmit} style={{ display: "grid", gap: "0.85rem" }}>
                        <label className="field">
                            <span>Email</span>
                            <input
                                className="input"
                                type="email"
                                placeholder="you@example.com"
                                autoComplete="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                            />
                        </label>
                        {needsPassword && (
                            <label className="field">
                                <span>Password{mode === "signUp" && ", at least 8 characters"}</span>
                                <input
                                    className="input"
                                    type="password"
                                    autoComplete={mode === "signUp" ? "new-password" : "current-password"}
                                    minLength={mode === "signUp" ? 8 : undefined}
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                />
                            </label>
                        )}
                        <button type="submit" className="btn btn-primary btn-wide" disabled={busy}>
                            {busy ? "One moment…" : SUBMIT[mode]}
                        </button>
                        {error && (
                            <p role="alert" className="alert">
                                {error}
                            </p>
                        )}
                    </form>
                </>
            )}
            <nav className="auth-links" aria-label="Other ways to sign in">
                {mode !== "signIn" && <button onClick={() => switchTo("signIn")}>Sign in with password</button>}
                {mode !== "signUp" && <button onClick={() => switchTo("signUp")}>Create an account</button>}
                {mode !== "reset" && <button onClick={() => switchTo("reset")}>Forgot password?</button>}
                {mode !== "link" && <button onClick={() => switchTo("link")}>Email me a link instead</button>}
            </nav>
        </AuthLayout>
    );
};

export default Login;
