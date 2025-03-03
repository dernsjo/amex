import axios from "axios";

const API_BASE_URL = "http://localhost:8000"; // Update if your FastAPI URL is different

// Fetch all users
export const getUsers = async () => {
    try {
        const response = await axios.get(`${API_BASE_URL}/users/`);
        return response.data;
    } catch (error) {
        console.error("Error fetching users:", error);
        return [];
    }
};

// Create a new user
export const createUser = async (name) => {
    try {
        await axios.post(`${API_BASE_URL}/users/`, { name });
    } catch (error) {
        console.error("Error creating user:", error);
    }
};

// Create a new expense
export const createExpense = async (expense) => {
    try {
        await axios.post(`${API_BASE_URL}/expenses/add-expense`, expense);
    } catch (error) {
        console.error("Error creating expense:", error);
    }
};

// Upload expenses from a file
export const uploadExpenses = async (file) => {
    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch(`${API_BASE_URL}/expenses/upload`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Failed to upload expenses");
        }

        return true;
    } catch (error) {
        console.error("Error uploading expenses:", error);
        return false;
    }
};

// Delete an expense
export const deleteExpense = async (expenseId) => {
    try {
        const response = await fetch(`${API_BASE_URL}/expenses/${expenseId}`, {
            method: "DELETE",
        });

        if (!response.ok) {
            throw new Error("Failed to delete expense");
        }

        return true;
    } catch (error) {
        console.error("Error deleting expense:", error);
        return false;
    }
};

// Fetch paid-by options
export const getPaidByOptions = async () => {
    try {
        const response = await axios.get(`${API_BASE_URL}/expenses/paid-by-options`);
        return response.data;
    } catch (error) {
        console.error("Error fetching paid-by options:", error);
        return [];
    }
};

// Update paid-by for an expense
export const updatePaidBy = async (expenseId, paidBy) => {
    try {
        const response = await axios.put(`${API_BASE_URL}/expenses/update-paid-by`, [
            { id: expenseId, paid_by: paidBy } // Send as an array
        ]);
        return response.data; // Return updated expenses
    } catch (error) {
        console.error("Error updating paid-by:", error);
        throw error; // Rethrow for handling in UI
    }
};


// Fetch all expenses
export const getExpenses = async () => {
    try {
        const response = await axios.get(`${API_BASE_URL}/expenses/`);
        return response.data;
    } catch (error) {
        console.error("Error fetching expenses:", error);
        return [];
    }
};

