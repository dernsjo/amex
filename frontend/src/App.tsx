import { useCallback, useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { errorMessage, getAccounts, getCategories, getMe, getTransactions, updateMe } from "./api";
import type { Account, Me, Transaction } from "./api";
import { supabase } from "./supabase";
import Login from "./components/Login";
import AccountPanel from "./components/AccountPanel";
import HouseholdPanel from "./components/HouseholdPanel";
import TransactionForm from "./components/TransactionForm";
import TransactionTable from "./components/TransactionTable";
import ImportWizard from "./components/ImportWizard";
import SettlementCard from "./components/SettlementCard";
import CategoryPanel from "./components/CategoryPanel";
import BudgetPanel from "./components/BudgetPanel";
import "./App.css";

function App() {
    const [session, setSession] = useState<Session | null | undefined>(undefined); // undefined: still loading

    useEffect(() => {
        supabase.auth.getSession().then(({ data }) => setSession(data.session));
        const { data } = supabase.auth.onAuthStateChange((_event, s) => setSession(s));
        return () => data.subscription.unsubscribe();
    }, []);

    if (session === undefined) return null;
    if (session === null) return <Login />;
    return <Home key={session.user.id} />;
}

function Home() {
    const [me, setMe] = useState<Me | null>(null);
    // null: everything you can see; a number: only what's shared into that household.
    const [householdId, setHouseholdId] = useState<number | null>(null);
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    // Category names per scope: "me" for your unshared accounts, else a household id.
    const [categories, setCategories] = useState<Record<string, string[]>>({});
    const [categoriesVersion, setCategoriesVersion] = useState(0);
    const [error, setError] = useState<string | null>(null);

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

    if (error) return <p role="alert">{error}</p>;
    if (!me) return null;

    const myAccounts = accounts.filter((a) => a.owner.user_id === me.id);
    // An account uses its household's categories when shared, else its owner's.
    const categoriesFor = (account: Account | undefined) => categories[account?.household_id ?? "me"] ?? [];
    const viewName = householdId ? me.households.find((h) => h.id === householdId)?.name : undefined;
    const handleCategoriesChanged = async () => {
        await fetchCategories(me.households);
        await fetchTransactions();
    };
    const handleRename = async () => {
        const name = window.prompt("Your name, as others in a household see it", me.display_name);
        if (name?.trim()) setMe(await updateMe(name.trim()));
    };

    return (
        <div style={{ textAlign: "center", padding: "20px" }}>
            <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <select
                    value={householdId ?? ""}
                    onChange={(e) => setHouseholdId(e.target.value ? Number(e.target.value) : null)}
                >
                    <option value="">My view</option>
                    {me.households.map((h) => (
                        <option key={h.id} value={h.id}>
                            {h.name}
                        </option>
                    ))}
                </select>
                <span>
                    <button onClick={handleRename}>{me.display_name}</button>{" "}
                    <button onClick={() => supabase.auth.signOut()}>Sign out</button>
                </span>
            </header>

            <h1>{viewName ?? "Spending"}</h1>

            <AccountPanel me={me} accounts={accounts} onChanged={() => fetchAll()} />

            <HouseholdPanel me={me} householdId={householdId} onChanged={fetchAll} />

            <ImportWizard accounts={myAccounts} onImported={() => fetchAll()} />

            <BudgetPanel householdId={householdId} transactions={transactions} categoriesVersion={categoriesVersion} />

            <CategoryPanel
                key={householdId ?? "me"}
                householdId={householdId}
                scopeName={viewName ?? "your own accounts"}
                onChanged={handleCategoriesChanged}
            />

            <TransactionForm accounts={myAccounts} categoriesFor={categoriesFor} fetchTransactions={fetchTransactions} />

            <TransactionTable
                me={me.id}
                transactions={transactions}
                accounts={accounts}
                categoriesFor={categoriesFor}
                fetchTransactions={fetchTransactions}
            />

            {householdId && <SettlementCard householdId={householdId} transactions={transactions} />}
        </div>
    );
}

export default App;
