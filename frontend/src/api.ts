import axios from "axios";
import { supabase } from "./supabase";

export const api = axios.create({
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
    pending: boolean; // added by email but hasn't signed in yet
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
    import_config: ImportConfig | null; // how the next upload will be read
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

export interface CsvMapping {
    date_column: string;
    description_column: string;
    amount_column: string;
    decimal_separator: "," | ".";
    spending_is_negative: boolean;
    date_format: string | null; // strptime format; null tries the common ones
}

export interface ImportConfig {
    importer: string; // a built-in importer id, or "csv" with a mapping
    mapping: CsvMapping | null;
}

export type SuggestedMapping = Omit<CsvMapping, "date_column" | "description_column" | "amount_column"> & {
    date_column: string | null;
    description_column: string | null;
    amount_column: string | null;
};

export interface ImportPreview {
    filename: string;
    config: ImportConfig | null;
    source: "requested" | "saved" | "detected" | "guessed" | "none";
    importers: { id: string; name: string }[];
    suggested_mapping: SuggestedMapping;
    columns: string[];
    sample_rows: string[][];
    transactions: {
        booked_on: string;
        description: string;
        amount_minor: number;
        category: string;
        duplicate: boolean;
    }[];
    new_count: number;
    duplicate_count: number;
    already_imported_at: string | null;
    error: string | null;
}

export interface ImportResult {
    id: number;
    account_id: number;
    importer: string;
    filename: string;
    period_start: string | null;
    period_end: string | null;
    transaction_count: number;
    duplicate_count: number;
    created_at: string;
}

export interface Category {
    id: number;
    name: string;
    is_fallback: boolean; // catches everything unmatched; can be renamed but not deleted
}

export interface CategoryRule {
    id: number;
    pattern: string; // matched case-insensitively within the description
    category: string;
}

export interface BudgetLine {
    category: string;
    recurring_minor: number | null; // the target for every month
    override_minor: number | null; // this month's own target
    target_minor: number | null; // what applies this month
    spent_minor: number;
}

export interface BudgetMonth {
    month: string; // YYYY-MM
    lines: BudgetLine[];
    target_minor: number;
    spent_minor: number;
}

export interface Summary extends BudgetMonth {
    largest: Transaction[]; // the biggest spending that counts in this view
    previous_spent_minor: number; // the month before
}

export interface Trends {
    months: { month: string; spent_minor: number; by_category: Record<string, number> }[]; // oldest first
}

export interface MemberShare extends Person {
    amount_minor: number; // responsible for: personal spending plus their part of shared
    paid_minor: number; // shared and personal spending on accounts they own
    balance_minor: number; // positive is owed money, negative owes
}

export interface Settlement {
    household_id: number;
    month: string; // YYYY-MM
    per_member: MemberShare[];
    transfers: { debtor: Person; creditor: Person; amount_minor: number }[];
    outlay_minor: number;
    shared_minor: number;
    total_minor: number;
    closed_at: string | null; // set when the month is closed and this is what was stored
}

/** The current month as YYYY-MM. */
export const thisMonth = () => {
    const today = new Date();
    return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
};

/** A YYYY-MM month moved by `delta` months. */
export const addMonths = (month: string, delta: number) => {
    const [year, m] = month.split("-").map(Number);
    const d = new Date(year, m - 1 + delta, 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
};

export const monthName = (month: string) =>
    new Date(`${month}-01T00:00:00`).toLocaleDateString("en-GB", { month: "long", year: "numeric" });

/** A YYYY-MM month as a short name, e.g. "Nov". */
export const monthShort = (month: string) =>
    new Date(`${month}-01T00:00:00`).toLocaleDateString("en-GB", { month: "short" });

/** An ISO date as e.g. "4 Nov". */
export const dayName = (iso: string) =>
    new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" });

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

/** Add by email; someone who hasn't signed in yet becomes a pending member under `displayName`. */
export const addMember = async (householdId: number, email: string, displayName?: string) =>
    (await api.post<Household>(`/households/${householdId}/members`, { email, display_name: displayName || null }))
        .data;

export const updateMember = async (
    householdId: number,
    userId: number,
    changes: Partial<Pick<Member, "split_weight" | "role">>,
) => (await api.patch<Household>(`/households/${householdId}/members/${userId}`, changes)).data;

export const removeMember = async (householdId: number, userId: number) => {
    await api.delete(`/households/${householdId}/members/${userId}`);
};

/** A closed month answers what was stored when it was closed. */
export const getSettlement = async (householdId: number, month: string) =>
    (await api.get<Settlement>(`/households/${householdId}/settlement`, { params: { month } })).data;

/** Closed months, newest first. */
export const getSettlements = async (householdId: number) =>
    (await api.get<Settlement[]>(`/households/${householdId}/settlements`)).data;

export const closeMonth = async (householdId: number, month: string) =>
    (await api.post<Settlement>(`/households/${householdId}/settlements`, { month })).data;

/** Owners only. */
export const reopenMonth = async (householdId: number, month: string) => {
    await api.delete(`/households/${householdId}/settlements/${month}`);
};

// Accounts

export const getAccounts = async () => (await api.get<Account[]>("/accounts")).data;

export const createAccount = async (name: string, household_id: number | null) =>
    (await api.post<Account>("/accounts", { name, household_id })).data;

export const updateAccount = async (accountId: number, changes: Partial<Pick<Account, "name" | "household_id">>) =>
    (await api.patch<Account>(`/accounts/${accountId}`, changes)).data;

export const deleteAccount = async (accountId: number) => {
    await api.delete(`/accounts/${accountId}`);
};

const importForm = (file: File, config?: ImportConfig) => {
    const formData = new FormData();
    formData.append("file", file);
    if (config) formData.append("config", JSON.stringify(config));
    return formData;
};

/** Read a file without storing anything. Without a config, the account's saved one or auto-detection is used. */
export const previewImport = async (accountId: number, file: File, config?: ImportConfig) =>
    (await api.post<ImportPreview>(`/accounts/${accountId}/imports/preview`, importForm(file, config))).data;

export const confirmImport = async (accountId: number, file: File, config?: ImportConfig) =>
    (await api.post<ImportResult>(`/accounts/${accountId}/imports`, importForm(file, config))).data;

export const getImports = async (accountId: number) =>
    (await api.get<ImportResult[]>(`/accounts/${accountId}/imports`)).data;

export const undoImport = async (accountId: number, importId: number) => {
    await api.delete(`/accounts/${accountId}/imports/${importId}`);
};

// Categories, rules and budgets: your own (householdId null) or a household's

const scope = (householdId: number | null) => ({ params: householdId ? { household_id: householdId } : {} });

export const getCategories = async (householdId: number | null) =>
    (await api.get<Category[]>("/categories", scope(householdId))).data;

export const createCategory = async (householdId: number | null, name: string) =>
    (await api.post<Category>("/categories", { name }, scope(householdId))).data;

/** The scope's transactions, rules and budgets follow the new name. */
export const renameCategory = async (householdId: number | null, categoryId: number, name: string) =>
    (await api.patch<Category>(`/categories/${categoryId}`, { name }, scope(householdId))).data;

export const deleteCategory = async (householdId: number | null, categoryId: number) => {
    await api.delete(`/categories/${categoryId}`, scope(householdId));
};

export const getRules = async (householdId: number | null) =>
    (await api.get<CategoryRule[]>("/category-rules", scope(householdId))).data;

/** Also re-categorizes the scope's transactions that nobody categorized by hand. */
export const createRule = async (householdId: number | null, pattern: string, category: string) =>
    (
        await api.post<{ rule: CategoryRule; recategorized: number }>(
            "/category-rules",
            { pattern, category },
            scope(householdId),
        )
    ).data;

export const deleteRule = async (householdId: number | null, ruleId: number) => {
    await api.delete(`/category-rules/${ruleId}`, scope(householdId));
};

/** Targets against spending: shared spending for a household, your own share for you. */
export const getBudgets = async (householdId: number | null, month: string) =>
    (await api.get<BudgetMonth>("/budgets", { params: { ...scope(householdId).params, month } })).data;

/** A target for every month (month null) or only one; amount null removes it. */
export const setBudget = async (
    householdId: number | null,
    category: string,
    month: string | null,
    amount_minor: number | null,
) => {
    await api.put("/budgets", { category, month, amount_minor }, scope(householdId));
};

/** Spending against targets for one month, the largest spending, and the month before's total. */
export const getSummary = async (householdId: number | null, month: string) =>
    (await api.get<Summary>("/summary", { params: { ...scope(householdId).params, month } })).data;

/** Spending per month and category, `from` through `to` (YYYY-MM). */
export const getTrends = async (householdId: number | null, from: string, to: string) =>
    (await api.get<Trends>("/trends", { params: { ...scope(householdId).params, from, to } })).data;

/** The start of a rule for a description: its first two words without digits, e.g. "PRESSBYRÅN STH". */
export const suggestPattern = (description: string) => {
    const words = description.split(/\s+/).filter((w) => w && !/\d/.test(w));
    return words.slice(0, 2).join(" ") || description.trim();
};

// Transactions

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
