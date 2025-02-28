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

