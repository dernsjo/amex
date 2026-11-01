import { useCallback, useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { errorMessage, getAccounts, getCategories, getMe, getTransactions, thisMonth, updateMe } from "./api";
import type { Account, Me, Transaction } from "./api";
import { supabase } from "./supabase";
import Login, { AuthLayout } from "./components/Login";
import SetPassword from "./components/SetPassword";
import AccountPanel from "./components/AccountPanel";
import HouseholdPanel from "./components/HouseholdPanel";
import TransactionForm from "./components/TransactionForm";
import TransactionTable from "./components/TransactionTable";
import ImportWizard from "./components/ImportWizard";
import SettlementCard from "./components/SettlementCard";
import CategoryPanel from "./components/CategoryPanel";
import BudgetPanel from "./components/BudgetPanel";
import Dashboard from "./components/Dashboard";
import { DialogProvider, Segmented, Wordmark, useDialogs } from "./components/ui";
import "./styles.css";

function App() {
    const [session, setSession] = useState<Session | null | undefined>(undefined); // undefined: still loading
    // Signed in by a password reset link: choose the new password before anything else.
    const [recovering, setRecovering] = useState(false);

    useEffect(() => {
        supabase.auth.getSession().then(({ data }) => setSession(data.session));
        const { data } = supabase.auth.onAuthStateChange((event, s) => {
            setSession(s);
            if (event === "PASSWORD_RECOVERY") setRecovering(true);
        });
        return () => data.subscription.unsubscribe();
    }, []);

    if (session === undefined) return null;
    if (session === null) return <Login />;
    if (recovering)
        return (
            <AuthLayout>
                <h1 className="head">Choose a new password</h1>
                <SetPassword onDone={() => setRecovering(false)} />
            </AuthLayout>
        );
    return (
        <DialogProvider>
            <Home key={session.user.id} />
        </DialogProvider>
    );
}

export type View = "overview" | "transactions" | "budget" | "settle" | "import" | "setup";

const VIEWS: { id: View; label: string; householdOnly?: boolean }[] = [
    { id: "overview", label: "Overview" },
    { id: "transactions", label: "Transactions" },
    { id: "budget", label: "Budget" },
    { id: "settle", label: "Settle up", householdOnly: true },
    { id: "import", label: "Import" },
    { id: "setup", label: "Setup" },
];

type SetupTab = "accounts" | "household" | "categories" | "you";

const viewFromHash = (): View => {
    const id = window.location.hash.slice(1);
    return VIEWS.some((v) => v.id === id) ? (id as View) : "overview";
};

/** The current view lives in the URL hash, so reloading and the back button keep your place. */
const useView = () => {
    const [view, setView] = useState<View>(viewFromHash);
    useEffect(() => {
        const onHash = () => setView(viewFromHash());
        window.addEventListener("hashchange", onHash);
        return () => window.removeEventListener("hashchange", onHash);
    }, []);
    const go = useCallback((next: View) => {
        window.location.hash = next;
        setView(next);
        window.scrollTo({ top: 0 });
    }, []);
    return [view, go] as const;
};

export function Home({ initialHouseholdId = null }: { initialHouseholdId?: number | null }) {
    const dialogs = useDialogs();
    const [me, setMe] = useState<Me | null>(null);
    // null: everything you can see; a number: only what's shared into that household.
    const [householdId, setHouseholdId] = useState<number | null>(initialHouseholdId);
    const [month, setMonth] = useState(thisMonth); // YYYY-MM, for the dashboard, budget and settlement
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    // Category names per scope: "me" for your unshared accounts, else a household id.
    const [categories, setCategories] = useState<Record<string, string[]>>({});
    const [categoriesVersion, setCategoriesVersion] = useState(0);
    const [error, setError] = useState<string | null>(null);
    const [view, go] = useView();
    const [setupTab, setSetupTab] = useState<SetupTab>("accounts");
    const [menuOpen, setMenuOpen] = useState(false);
    const [passwordSaved, setPasswordSaved] = useState(false);

    const fetchAccounts = useCallback(async () => {
        setAccounts(await getAccounts());
    }, []);

    const fetchCategories = useCallback(async (households: Me["households"]) => {
        const scopes = [null, ...households.map((h) => h.id)];
        const lists = await Promise.all(scopes.map((id) => getCategories(id)));
        setCategories(Object.fromEntries(scopes.map((id, i) => [id ?? "me", lists[i].map((c) => c.name)])));
        setCategoriesVersion((v) => v + 1);
    }, []);

    const fetchTransactions = useCallback(async () => {
        setTransactions(await getTransactions(householdId));
    }, [householdId]);

    const fetchAll = useCallback(
        async (selectHouseholdId?: number | null) => {
            const fresh = await getMe();
            setMe(fresh);
            await fetchCategories(fresh.households);
            if (selectHouseholdId !== undefined) setHouseholdId(selectHouseholdId);
            await fetchAccounts();
            await fetchTransactions();
        },
        [fetchAccounts, fetchCategories, fetchTransactions],
    );

    useEffect(() => {
        getMe()
            .then((fresh) => {
                setMe(fresh);
                return fetchCategories(fresh.households);
            })
            .catch((e) => setError(errorMessage(e)));
        fetchAccounts();
    }, [fetchAccounts, fetchCategories]);

    useEffect(() => {
        // A household you were removed from answers 404; fall back to your own view.
        fetchTransactions().catch((e) => (householdId ? setHouseholdId(null) : setError(errorMessage(e))));
    }, [fetchTransactions, householdId]);

    // Settling up only exists inside a household.
    useEffect(() => {
        if (view === "settle" && householdId === null && me) go("overview");
    }, [view, householdId, me, go]);

    if (error)
        return (
            <p role="alert" className="alert" style={{ margin: "2rem" }}>
                {error}
            </p>
        );
    if (!me) return null;

    const myAccounts = accounts.filter((a) => a.owner.user_id === me.id);
    // An account uses its household's categories when shared, else its owner's.
    const categoriesFor = (account: Account | undefined) => categories[account?.household_id ?? "me"] ?? [];
    const household = me.households.find((h) => h.id === householdId);
    const viewName = household?.name;
    const handleCategoriesChanged = async () => {
        await fetchCategories(me.households);
        await fetchTransactions();
    };
    const handleRename = async () => {
        const name = await dialogs.prompt("Your name", "As others in a household see it", me.display_name);
        if (name?.trim()) setMe(await updateMe(name.trim()));
    };
    const openSetup = (tab: SetupTab) => {
        setSetupTab(tab);
        go("setup");
    };

    const navItems = VIEWS.filter((v) => !v.householdOnly || household);

    return (
        <div className="shell">
            <header className="rail">
                <div className="rail-top">
                    <a href="#overview" onClick={() => go("overview")} aria-label="Leva, overview" style={{ textDecoration: "none" }}>
                        <Wordmark />
                    </a>
                    <button
                        type="button"
                        className="btn btn-small menu-toggle"
                        aria-expanded={menuOpen}
                        onClick={() => setMenuOpen(!menuOpen)}
                    >
                        {me.display_name}
                    </button>
                </div>

                <label className="scope">
                    <span className="scope-label">Showing</span>
                    <select
                        className="select"
                        value={householdId ?? ""}
                        onChange={(e) => setHouseholdId(e.target.value ? Number(e.target.value) : null)}
                    >
                        <option value="">Just me</option>
                        {me.households.map((h) => (
                            <option key={h.id} value={h.id}>
                                {h.name}
                            </option>
                        ))}
                    </select>
                </label>

                <nav className="nav" aria-label="Main">
                    {navItems.map((v) => (
                        <a
                            key={v.id}
                            href={`#${v.id}`}
                            aria-current={view === v.id ? "page" : undefined}
                            onClick={(e) => {
                                e.preventDefault();
                                go(v.id);
                            }}
                        >
                            {v.label}
                        </a>
                    ))}
                </nav>

                <div className={`rail-foot${menuOpen ? " open" : ""}`}>
                    <div>
                        <p className="me-name">{me.display_name}</p>
                        <p className="me-email">{me.email}</p>
                    </div>
                    <div className="me-actions">
                        <button className="link" onClick={handleRename}>
                            Change name
                        </button>
                        <button className="link" onClick={() => openSetup("you")}>
                            Password
                        </button>
                        <button className="link" onClick={() => supabase.auth.signOut()}>
                            Sign out
                        </button>
                    </div>
                </div>
            </header>

            <main className="main" id="main">
                {view === "overview" && (
                    <Dashboard
                        householdId={householdId}
                        householdName={viewName}
                        month={month}
                        onMonthChange={setMonth}
                        transactions={transactions}
                        categoriesVersion={categoriesVersion}
                        hasAccounts={accounts.length > 0}
                        onGo={go}
                    />
                )}

                {view === "transactions" && (
                    <div className="view">
                        <div className="view-head">
                            <div>
                                <h1 className="head">Transactions</h1>
                                <p>
                                    {viewName ? `Spending on accounts shared with ${viewName}.` : "Everything you can see."}{" "}
                                    Choose a row to change its category or how it's split.
                                </p>
                            </div>
                        </div>
                        <TransactionForm accounts={myAccounts} categoriesFor={categoriesFor} fetchTransactions={fetchTransactions} />
                        <TransactionTable
                            me={me.id}
                            transactions={transactions}
                            accounts={accounts}
                            categoriesFor={categoriesFor}
                            fetchTransactions={fetchTransactions}
                        />
                    </div>
                )}

                {view === "budget" && (
                    <BudgetPanel
                        householdId={householdId}
                        month={month}
                        onMonthChange={setMonth}
                        transactions={transactions}
                        categoriesVersion={categoriesVersion}
                    />
                )}

                {view === "settle" && household && (
                    <SettlementCard
                        householdId={household.id}
                        householdName={household.name}
                        month={month}
                        onMonthChange={setMonth}
                        isOwner={household.role === "owner"}
                        transactions={transactions}
                    />
                )}

                {view === "import" && (
                    <ImportWizard accounts={myAccounts} onImported={() => fetchAll()} onAddAccount={() => openSetup("accounts")} />
                )}

                {view === "setup" && (
                    <div className="view">
                        <div className="view-head">
                            <div>
                                <h1 className="head">Setup</h1>
                                <p>Accounts, who you share with, and how spending is sorted.</p>
                            </div>
                        </div>
                        <Segmented
                            label="Setup section"
                            value={setupTab}
                            onChange={setSetupTab}
                            options={[
                                { value: "accounts", label: "Accounts" },
                                { value: "household", label: "Household" },
                                { value: "categories", label: "Categories and rules" },
                                { value: "you", label: "You" },
                            ]}
                        />
                        {setupTab === "accounts" && <AccountPanel me={me} accounts={accounts} onChanged={() => fetchAll()} />}
                        {setupTab === "household" && (
                            <HouseholdPanel me={me} householdId={householdId} onChanged={fetchAll} />
                        )}
                        {setupTab === "categories" && (
                            <CategoryPanel
                                key={householdId ?? "me"}
                                householdId={householdId}
                                scopeName={viewName ?? "your own accounts"}
                                onChanged={handleCategoriesChanged}
                            />
                        )}
                        {setupTab === "you" && (
                            <section className="block">
                                <div className="block-head">
                                    <h2>{me.display_name}</h2>
                                    <button className="link" onClick={handleRename}>
                                        Change name
                                    </button>
                                </div>
                                <p className="muted">{me.email}</p>
                                <h2 className="lead" style={{ marginTop: "1.5rem" }}>
                                    Password
                                </h2>
                                <p>Set a password to sign in without waiting for an email link.</p>
                                {passwordSaved ? (
                                    <p role="status" className="status">
                                        Password saved. You can now sign in with it.
                                    </p>
                                ) : (
                                    <SetPassword onDone={() => setPasswordSaved(true)} />
                                )}
                            </section>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}

export default App;
