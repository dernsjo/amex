import React, { useState, useEffect } from "react";
import { getUsers, createUser, getPaidByOptions, getExpenses, createExpense, deleteExpense, uploadExpenses, updatePaidBy} from "./api";
import './App.css';

function App() {
    const [users, setUsers] = useState([]);
    const [name, setName] = useState("");

    const [paidByOptions, setPaidByOptions] = useState([]);
    const [selectedPaidBy, setSelectedPaidBy] = useState("Split");
    const [updatedPaidBy, setUpdatedPaidBy] = useState("");
    const [editingExpenseId, setEditingExpenseId] = useState(null);

    const [expenses, setExpenses] = useState([]);
    const [description, setDescription] = useState("");  // Input for expense description
    const [amount, setAmount] = useState("");  // Input for expense amount
    const [paidBy, setPaidBy] = useState("");  // Input for expense paid-by
    const [file, setFile] = useState(null);  // Input for file upload

    useEffect(() => {
      getPaidByOptions().then(setPaidByOptions);
      getExpenses().then(setExpenses); // Fetch expenses from the backend
    }, []);

    // Function to fetch users
    const fetchUsers = async () => {
      const usersData = await getUsers();
      setUsers(usersData);
    };

    // Function to create a user
    const handleCreateUser = async (event) => {
        event.preventDefault();
        await createUser(name);
        setName(""); // Clear input
        fetchUsers(); // Refresh user list
    };

    // Handle the form submission to save the expense
    const handleAddExpense = async (event) => {
      event.preventDefault();

      // Create a new expense object
      const newExpense = {
          description,
          amount: parseFloat(amount),  // Make sure amount is a number
          paid_by: paidBy,
          date: new Date().toISOString(), // Assuming current date, adjust if needed
      };

      // Call the createExpense API to save the new expense
      await createExpense(newExpense);

      // After saving, clear the form and fetch the updated expenses list
      setDescription("");
      setAmount("");
      setPaidBy("Split");  // Reset to default option
      getExpenses().then(setExpenses);  // Fetch the updated expenses list
    };

    // Handle file selection
    const handleFileChange = (event) => {
        setFile(event.target.files[0]); // Store selected file
    };

    // Function to upload expenses from a file
    const handleUpload = async () => {
        if (!file) {
            alert("Please select a CSV file to upload.");
            return;
        }

        const success = await uploadExpenses(file);
        if (success) {
            getExpenses().then(setExpenses); // Refresh list after upload
        } else {
            alert("Failed to upload expenses.");
        }
    };


    // Function to fetch expenses
    const fetchExpenses = async () => {
        const expensesData = await getExpenses();
        setExpenses(expensesData);
    }

    // Function to delete an expense
    const handleDeleteExpense = async (expenseId) => {
        const success = await deleteExpense(expenseId);
        if (success) {
            setExpenses(expenses.filter(expense => expense.id !== expenseId)); // Remove from state
        } else {
            alert("Failed to delete expense");
        }
    };

    const startEditing = (expenseId, currentPaidBy) => {
        setEditingExpenseId(expenseId);
        setUpdatedPaidBy(currentPaidBy);
      };

    // Function to update paid-by for an expense
    const handleUpdatePaidBy = async (expenseId, newPaidBy) => {
        setEditingExpenseId(null); // Close dropdown after selecting
    
        try {
            const updatedExpenses = await updatePaidBy(expenseId, newPaidBy); // Use API function
    
            setExpenses((prevExpenses) =>
                prevExpenses.map((exp) =>
                    exp.id === expenseId ? { ...exp, paid_by: newPaidBy } : exp
                )
            );
        } catch (error) {
            console.error("Error updating paid_by:", error);
        }
    };


    return (
        <div style={{ textAlign: "center", padding: "20px" }}>
            <h1>Expense Tracker</h1>

            {/* Create User Form */}
            <h2>Create User</h2>
            <form onSubmit={handleCreateUser}>
                <input
                    type="text"
                    placeholder="Enter user name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                />
                <button type="submit">Create User</button>
            </form>

            {/* Fetch Users Button */}
            <h2>Users</h2>
            <button onClick={fetchUsers}>Load Users</button>

            {/* Display Users */}
            <ul>
                {users.map((user) => (
                    <li key={user.id}>{user.name}</li>
                ))}
            </ul>

            {/* Paid-By Options */}
            <h2>Paid-By Options</h2>
            <select
                value={selectedPaidBy}
                onChange={(e) => setSelectedPaidBy(e.target.value)}
            >
                {paidByOptions.map((option) => (
                    <option key={option} value={option}>
                        {option}
                    </option>
                ))}
            </select>
            <br />
            <br />
            
            {/* Upload Expenses */}
            <h2>Upload Expenses</h2>
            <input type="file" accept=".csv" onChange={handleFileChange} />
            <button onClick={handleUpload}>Upload</button>

            {/* Add Expense Form */}
            <h2>Add Expense</h2>
            <form onSubmit={handleAddExpense}>
                <div>
                  <label>Description: </label>
                    <input
                        type="text"
                        placeholder="Enter description"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}  
                        required
                    />
                </div>

                <div>
                  <label>Amount: </label>
                    <input
                        type="number"
                        placeholder="Enter amount"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        required
                    />
                </div>

                <div>
                  <label>Paid By: </label>
                    <select
                        value={paidBy}
                        onChange={(e) => setPaidBy(e.target.value)}
                        >
                        {paidByOptions.length > 0 ? (
                            paidByOptions.map((option) => (
                                <option key={option} value={option}>
                                    {option}
                                </option>
                            ))
                        ) : (
                            <option value="Split">Split</option> // Default option
                        )}
                    </select>
                </div>
                {/* Submit Button */}
    <           button type="submit">Add Expense</button>
            </form>
    
            {/* Fetch Expenses Button */}
            <br />
            <button onClick={fetchExpenses}>Load Expenses</button>

            {/* Display Expenses in Table */}
            <h3>Expense table</h3>
            <table border="1" style={{ width: "100%", marginBottom: "20px", borderCollapse: "collapse" }}>
                <thead>
                    <tr>
                        <th>Description</th>
                        <th>Amount</th>
                        <th>Paid By</th>
                    </tr>
                </thead>
                <tbody>
                    {expenses.map((expense) => (
                        <tr key={expense.id}>
                            <td>{expense.description}</td>
                            <td>{expense.amount}</td>
                            <td>
                            {editingExpenseId === expense.id ? (
                              <select
                                value={updatedPaidBy}
                                onChange={(e) => setUpdatedPaidBy(e.target.value)}
                                onBlur={() => handleUpdatePaidBy(expense.id)} // Save on blur
                              >
                                {paidByOptions.map((option) => (
                                  <option key={option} value={option}>
                                    {option}
                                  </option>
                                ))}
                              </select>
                            ) : (
                              <span onClick={() => startEditing(expense.id, expense.paid_by)}>
                                {expense.paid_by}
                              </span>
                            )}
                            </td>
                            <td>
                                <button onClick={() => handleDeleteExpense(expense.id)}>Delete</button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>

        </div>
    );
}

export default App;