import axios from "axios";
import { supabase } from "./supabase";

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
});

// Every request carries the Supabase access token; supabase-js refreshes it as needed.
api.interceptors.request.use(async (config) => {
    const { data } = await supabase.auth.getSession();
    if (data.session) config.headers.Authorization = `Bearer ${data.session.access_token}`;
    return config;
});

export type Role = "owner" | "member";
export type Allocation = "shared" | "personal" | "outlay" | "excluded";
export const ALLOCATIONS: Allocation[] = ["shared", "personal", "outlay", "excluded"];

export interface Person {
    user_id: number;
    display_name: string;
}

export interface Me {
    id: number;
    email: string;
    display_name: string;
    households: { id: number; name: string; role: Role }[];
}

export interface Member extends Person {
    email: string;
    role: Role;
    split_weight: number;
}

export interface Household {
    id: number;
    name: string;
    members: Member[];
}

export interface Account {
    id: number;
    name: string;
    currency: string;
    owner: Person;
    household_id: number | null;
    members: Person[]; // who a transaction can be marked as personal for
}

export interface Transaction {
    id: number;
    account_id: number;
    import_id: number | null;
    booked_on: string; // ISO date, YYYY-MM-DD
    description: string;
    amount_minor: number;
    currency: string;
    allocation: Allocation;
    member_id: number | null;
    category: string | null;
}

export interface NewTransaction {
    description: string;
    amount: number;
    booked_on?: string;
    category?: string;
}

export interface ImportResult {
    id: number;
    filename: string;
    transaction_count: number;
    duplicate_count: number;
}

export interface Settlement {
    household_id: number;
    per_member: (Person & { amount_minor: number })[];
    outlay_minor: number;
    shared_minor: number;
    total_minor: number;
}

/** Format öre as kronor. */
export const kr = (minor: number, currency = "SEK") =>
    (minor / 100).toLocaleString("sv-SE", { style: "currency", currency });

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

// Me and households

export const getMe = async () => (await api.get<Me>("/me")).data;

export const updateMe = async (display_name: string) => (await api.patch<Me>("/me", { display_name })).data;

export const createHousehold = async (name: string) => (await api.post<Household>("/households", { name })).data;

export const getHousehold = async (id: number) => (await api.get<Household>(`/households/${id}`)).data;

export const addMember = async (householdId: number, email: string) =>
    (await api.post<Household>(`/households/${householdId}/members`, { email })).data;

export const updateMember = async (
    householdId: number,
    userId: number,
    changes: Partial<Pick<Member, "split_weight" | "role">>,
) => (await api.patch<Household>(`/households/${householdId}/members/${userId}`, changes)).data;

export const removeMember = async (householdId: number, userId: number) => {
    await api.delete(`/households/${householdId}/members/${userId}`);
};

export const getSettlement = async (householdId: number) =>
    (await api.get<Settlement>(`/households/${householdId}/settlement`)).data;

// Accounts

export const getAccounts = async () => (await api.get<Account[]>("/accounts")).data;

export const createAccount = async (name: string, household_id: number | null) =>
    (await api.post<Account>("/accounts", { name, household_id })).data;

export const updateAccount = async (accountId: number, changes: Partial<Pick<Account, "name" | "household_id">>) =>
    (await api.patch<Account>(`/accounts/${accountId}`, changes)).data;

export const deleteAccount = async (accountId: number) => {
    await api.delete(`/accounts/${accountId}`);
};

export const uploadImport = async (accountId: number, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return (await api.post<ImportResult>(`/accounts/${accountId}/imports`, formData)).data;
};

// Transactions

export const getCategories = async () => (await api.get<string[]>("/categories")).data;

/** Everything visible to the user, or only what's shared into one household. */
export const getTransactions = async (householdId: number | null) =>
    (await api.get<Transaction[]>("/transactions", { params: householdId ? { household_id: householdId } : {} }))
        .data;

export const createTransaction = async (accountId: number, transaction: NewTransaction) =>
    (await api.post<Transaction>(`/accounts/${accountId}/transactions`, transaction)).data;

export type TransactionChanges = Partial<Pick<Transaction, "allocation" | "member_id" | "category">>;

export const updateTransaction = async (transactionId: number, changes: TransactionChanges) =>
    (await api.patch<Transaction[]>("/transactions", [{ id: transactionId, ...changes }])).data;

export const deleteTransaction = async (transactionId: number) => {
    await api.delete(`/transactions/${transactionId}`);
};
