import React, { useState, useEffect } from "react";
import { getUsers, getPaidByOptions, getExpenses } from "./api";
import UserLoader from "./components/UserLoader"; // Import the new component
import UserForm from "./components/UserForm";
import ExpenseForm from "./components/ExpenseForm";
import ExpenseTable from "./components/ExpenseTable";
import "./App.css";

function App() {
    const [users, setUsers] = useState([]);
    const [paidByOptions, setPaidByOptions] = useState([]);
    const [expenses, setExpenses] = useState([]);

    useEffect(() => {
        getPaidByOptions().then(setPaidByOptions);
        fetchExpenses();
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

            <UserForm fetchUsers={fetchUsers} />
            
            {/* Replace the old users section with the new component */}
            <UserLoader users={users} fetchUsers={fetchUsers} />
            
            <ExpenseForm paidByOptions={paidByOptions} fetchExpenses={fetchExpenses} />
            
            <ExpenseTable expenses={expenses} paidByOptions={paidByOptions} fetchExpenses={fetchExpenses} />
        </div>
    );
}

export default App;