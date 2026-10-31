import { useCallback, useEffect, useState } from "react";
import { getCategories, getExpenses, getPaidByOptions, getUsers } from "./api";
import type { Expense, User } from "./api";
import UserCreator from "./components/UserCreator";
import UserTable from "./components/UserTable";
import ExpenseForm from "./components/ExpenseForm";
import ExpenseTable from "./components/ExpenseTable";
import TransactionUploader from "./components/TransactionUploader";
import ExpenseSplitter from "./components/ExpenseSplitter";
import "./App.css";

function App() {
    const [paidByOptions, setPaidByOptions] = useState<string[]>([]);
    const [categories, setCategories] = useState<string[]>([]);
    const [expenses, setExpenses] = useState<Expense[]>([]);
    const [users, setUsers] = useState<User[]>([]);

    // Paid-by options include user names, so refresh them whenever users change.
    const fetchUsers = useCallback(async () => {
        const [usersData, options] = await Promise.all([getUsers(), getPaidByOptions()]);
        setUsers(usersData);
        setPaidByOptions(options);
    }, []);

    const fetchExpenses = useCallback(async () => {
        setExpenses(await getExpenses());
    }, []);

    useEffect(() => {
        getCategories().then(setCategories);
        fetchUsers();
        fetchExpenses();
    }, [fetchUsers, fetchExpenses]);

    return (
        <div style={{ textAlign: "center", padding: "20px" }}>
            <h1>Expense Tracker</h1>

            <UserTable users={users} fetchUsers={fetchUsers} />

            <UserCreator fetchUsers={fetchUsers} />

            <TransactionUploader onTransactionsLoaded={fetchExpenses} />

            <ExpenseForm paidByOptions={paidByOptions} categories={categories} fetchExpenses={fetchExpenses} />

            <ExpenseTable
                expenses={expenses}
                paidByOptions={paidByOptions}
                categories={categories}
                fetchExpenses={fetchExpenses}
            />

            <ExpenseSplitter expenses={expenses} />
        </div>
    );
}

export default App;
