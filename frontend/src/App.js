import React, { useState, useEffect } from "react";
import { getUsers, getPaidByOptions, getExpenses } from "./api";
import CreateUser from "./components/UpdateUser";
import UserTable from "./components/UserTable";
import ExpenseForm from "./components/ExpenseForm";
import ExpenseTable from "./components/ExpenseTable";
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

    return (
        <div style={{ textAlign: "center", padding: "20px" }}>
            <h1>Expense Tracker</h1>

            {/* User Table */}
            <UserTable fetchUsers={fetchUsers} users={users} />

            {/* Create User */}
            <CreateUser fetchUsers={fetchUsers} />
            
            {/* Expense Form */}
            <ExpenseForm paidByOptions={paidByOptions} fetchExpenses={fetchExpenses} />
            
            {/* Expense Table */}
            <ExpenseTable expenses={expenses} paidByOptions={paidByOptions} fetchExpenses={fetchExpenses} />
        </div>
    );
}

export default App;
