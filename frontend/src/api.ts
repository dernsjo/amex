import axios from "axios";

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
});

export interface User {
    id: number;
    name: string;
    active: boolean;
}

export interface Expense {
    id: number;
    date: string; // ISO date, YYYY-MM-DD
    description: string;
    amount: number;
    paid_by: string;
    category: string | null;
}

export interface NewExpense {
    description: string;
    amount: number;
    paid_by: string;
    date?: string;
    category?: string;
}

export interface Settlement {
    per_member: Record<string, number>;
    outlay: number;
    shared: number;
    total: number;
}

/** Turn an API error into a message suitable for showing the user. */
export const errorMessage = (error: unknown): string => {
    if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        if (typeof detail === "string") return detail;
        if (Array.isArray(detail)) return detail.map((d) => d.msg).join("; ");
        return error.message;
    }
    return String(error);
};

export const getUsers = async () => (await api.get<User[]>("/users")).data;

export const createUser = async (name: string) => (await api.post<User>("/users", { name })).data;

export const deleteUser = async (userId: number) => {
    await api.delete(`/users/${userId}`);
};

export const getPaidByOptions = async () => (await api.get<string[]>("/expenses/paid-by-options")).data;

export const getExpenses = async () => (await api.get<Expense[]>("/expenses")).data;

export const createExpense = async (expense: NewExpense) => (await api.post<Expense>("/expenses", expense)).data;

export const getCategories = async () => (await api.get<string[]>("/expenses/categories")).data;

export type ExpenseChanges = Partial<Pick<Expense, "paid_by" | "category">>;

export const updateExpense = async (expenseId: number, changes: ExpenseChanges) =>
    (await api.patch<Expense[]>("/expenses", [{ id: expenseId, ...changes }])).data;

export const deleteExpense = async (expenseId: number) => {
    await api.delete(`/expenses/${expenseId}`);
};

export const uploadExpenses = async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return (await api.post<Expense[]>("/expenses/upload", formData)).data;
};

export const getSettlement = async () => (await api.get<Settlement>("/expenses/settlement")).data;
