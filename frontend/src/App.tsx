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
import TransactionUploader from "./components/TransactionUploader";
import SettlementCard from "./components/SettlementCard";
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
    const [categories, setCategories] = useState<string[]>([]);
    const [error, setError] = useState<string | null>(null);

    const fetchAccounts = useCallback(async () => {
        setAccounts(await getAccounts());
    }, []);

    const fetchTransactions = useCallback(async () => {
        setTransactions(await getTransactions(householdId));
    }, [householdId]);

    const fetchAll = useCallback(
        async (selectHouseholdId?: number | null) => {
            setMe(await getMe());
            if (selectHouseholdId !== undefined) setHouseholdId(selectHouseholdId);
            await fetchAccounts();
            await fetchTransactions();
        },
        [fetchAccounts, fetchTransactions],
    );

    useEffect(() => {
        getCategories().then(setCategories);
        getMe()
            .then(setMe)
            .catch((e) => setError(errorMessage(e)));
        fetchAccounts();
    }, [fetchAccounts]);

    useEffect(() => {
        // A household you were removed from answers 404; fall back to your own view.
        fetchTransactions().catch((e) => (householdId ? setHouseholdId(null) : setError(errorMessage(e))));
    }, [fetchTransactions, householdId]);

    if (error) return <p role="alert">{error}</p>;
    if (!me) return null;

    const myAccounts = accounts.filter((a) => a.owner.user_id === me.id);
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

            <h1>{householdId ? me.households.find((h) => h.id === householdId)?.name : "Spending"}</h1>

            <AccountPanel me={me} accounts={accounts} onChanged={() => fetchAll()} />

            <HouseholdPanel me={me} householdId={householdId} onChanged={fetchAll} />

            <TransactionUploader accounts={myAccounts} onTransactionsLoaded={fetchTransactions} />

            <TransactionForm accounts={myAccounts} categories={categories} fetchTransactions={fetchTransactions} />

            <TransactionTable
                me={me.id}
                transactions={transactions}
                accounts={accounts}
                categories={categories}
                fetchTransactions={fetchTransactions}
            />

            {householdId && <SettlementCard householdId={householdId} transactions={transactions} />}
        </div>
    );
}

export default App;
