import axios from "axios";

const API_BASE_URL = "http://localhost:8000"; // Update if needed

// Helper function to handle API requests
const apiRequest = async (method, url, data = null) => {
    try {
        const config = {
            method,
            url: `${API_BASE_URL}${url}`,
        };

        if (method.toLowerCase() === "get" || method.toLowerCase() === "delete") {
            config.params = data;  // Send data as query parameters
        } else {
            config.data = data;  // Send data in request body
        }

        const response = await axios(config);
        return response.data;
    } catch (error) {
        console.error(`API Error (${method} ${url}):`, error.response?.data || error.message);
        throw error; // Propagate error for proper handling in components
    }
};

// Fetch all users
export const getUsers = () => apiRequest("get", "/users/");

// Create a new user
export const createUser = (name) => apiRequest("post", "/users/", { name });

// Delete a user
export const deleteUser = (userId) => apiRequest("delete", "/users/delete-user", { user_id: userId });

// Fetch paid-by options
export const getPaidByOptions = () => apiRequest("get", "/expenses/paid-by-options");

// Fetch all expenses
export const getExpenses = () => apiRequest("get", "/expenses/");

// Create a new expense
export const createExpense = (expense) => apiRequest("post", "/expenses/add-expense", expense);

// Update paid-by for an expense
export const updatePaidBy = (expenseId, newPaidBy) => 
    apiRequest("put", `/expenses/update-paid-by`, [{ id: expenseId, paid_by: newPaidBy }]);

// Delete an expense
export const deleteExpense = (expenseId) => 
    apiRequest("delete", "/expenses/delete-expense", {expense_id: expenseId});

// Upload expenses via CSV
export const uploadExpenses = async (file) => {
    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await axios.post(`${API_BASE_URL}/expenses/upload`, formData, {
            headers: { "Content-Type": "multipart/form-data" },
        });
        return response.data;
    } catch (error) {
        console.error("Error uploading expenses:", error);
        return false; // Return false to indicate failure
    }
};

export const calculateExpenseSplit = async (expenses) => {
    try {
        const response = await fetch("/api/expenses/calculate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ expenses }),  // Send expenses to backend
        });

        if (!response.ok) {
            throw new Error("Failed to calculate expense split");
        }

        return await response.json();  // Return the response body (the calculated split)
    } catch (error) {
        console.error("Error calculating expense split:", error);
        throw new Error("Error calculating expense split");
    }
};
