import React, { useState, useEffect } from "react";
import { getUsers, getPaidByOptions, getExpenses } from "./api";
import CreateUser from "./components/UpdateUser";
import UserTable from "./components/UserTable";
import ExpenseForm from "./components/ExpenseForm";
import ExpenseTable from "./components/ExpenseTable";
import TransactionUploader from "./components/csvUploader";
import ExpenseSplitter from "./components/expenseSplitter";
import "./App.css";

function App() {
    const [paidByOptions, setPaidByOptions] = useState([]);
    const [expenses, setExpenses] = useState([]);
    const [users, setUsers] = useState([]);

    // Fetch data on initial load
    useEffect(() => {
        getPaidByOptions().then(setPaidByOptions);
        fetchUsers();
        fetchExpenses(); // Initial fetch of expenses
    }, []);

    const fetchUsers = async () => {
        const usersData = await getUsers();
        setUsers(usersData);
    };

    const fetchExpenses = async () => {
        const expensesData = await getExpenses();
        setExpenses(expensesData);
    };

    // This is the function that will be passed to TransactionUploader
    const onTransactionsLoaded = () => {
        fetchExpenses(); // Refresh the expenses after upload
    };

    return (
        <div style={{ textAlign: "center", padding: "20px" }}>
            <h1>Expense Tracker</h1>

            {/* User Table */}
            <UserTable fetchUsers={fetchUsers} users={users} />

            {/* Create User */}
            <CreateUser fetchUsers={fetchUsers} />

            {/* Transaction Uploader */}
            <TransactionUploader onTransactionsLoaded={onTransactionsLoaded} />

            {/* Expense Form */}
            <ExpenseForm paidByOptions={paidByOptions} fetchExpenses={fetchExpenses} />
            
            {/* Expense Table */}
            <ExpenseTable expenses={expenses} paidByOptions={paidByOptions} fetchExpenses={fetchExpenses} />

            {/* Expense Splitter */}
            <ExpenseSplitter expenses={expenses} />
            
        </div>
    );
}

export default App;