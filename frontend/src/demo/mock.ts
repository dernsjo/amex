/**
 * Sample data for demo.html: the signed-in app without a backend or Supabase.
 * Dev only (Vite serves demo.html; the production build only bundles index.html).
 * Every figure here is invented.
 */
import type { AxiosAdapter, InternalAxiosRequestConfig } from "axios";
import type {
    Account,
    BudgetMonth,
    Category,
    CategoryRule,
    Household,
    ImportResult,
    Me,
    Settlement,
    Summary,
    Transaction,
    Trends,
} from "../api";
import { addMonths, thisMonth } from "../api";

const month = thisMonth();
const day = (d: number, m = month) => `${m}-${String(d).padStart(2, "0")}`;

const alex = { user_id: 1, display_name: "Alex" };
const sam = { user_id: 2, display_name: "Sam" };

const me: Me = {
    id: 1,
    email: "alex@example.com",
    display_name: "Alex",
    households: [{ id: 10, name: "Home", role: "owner" }],
};

const household: Household = {
    id: 10,
    name: "Home",
    members: [
        { ...alex, email: "alex@example.com", role: "owner", split_weight: 3, pending: false },
        { ...sam, email: "sam@example.com", role: "member", split_weight: 2, pending: false },
    ],
};

const accounts: Account[] = [
    { id: 1, name: "Amex", currency: "SEK", owner: alex, household_id: 10, import_config: { importer: "amex_se", mapping: null }, members: [alex, sam] },
    { id: 2, name: "Joint card", currency: "SEK", owner: sam, household_id: 10, import_config: null, members: [alex, sam] },
    { id: 3, name: "Savings", currency: "SEK", owner: alex, household_id: null, import_config: null, members: [alex] },
];

const rows: [number, string, number, string, Transaction["allocation"], number, number | null][] = [
    [28, "ICA MAXI LINDHAGEN", 1_284_50, "Groceries", "shared", 1, null],
    [27, "SL ACCESS", 1_010_00, "Transport", "personal", 1, 1],
    [26, "SYSTEMBOLAGET ODENPLAN", 489_00, "Groceries", "shared", 2, null],
    [25, "RESTAURANG PELIKAN", 1_240_00, "Eating out", "shared", 1, null],
    [24, "ELLEVIO AB", 862_00, "Home", "shared", 2, null],
    [22, "APOTEK HJARTAT", 214_90, "Health", "personal", 2, 2],
    [21, "PRESSBYRAN STH C", 64_00, "Eating out", "personal", 1, 1],
    [19, "IKEA BARKARBY", 2_349_00, "Home", "shared", 1, null],
    [18, "SPOTIFY P1A2B3", 189_00, "Subscriptions", "shared", 2, null],
    [17, "COOP KONSUM VASASTAN", 642_30, "Groceries", "shared", 2, null],
    [15, "SJ AB BILJETT", 1_495_00, "Transport", "outlay", 1, null],
    [14, "BETALNING TACK", -8_400_00, "Other", "excluded", 1, null],
    [12, "HEMKOP TORSPLAN", 418_75, "Groceries", "shared", 1, null],
    [9, "BIO RIO", 300_00, "Eating out", "shared", 2, null],
    [6, "TELIA SVERIGE", 449_00, "Subscriptions", "shared", 1, null],
    [3, "WILLYS ODENPLAN", 1_106_20, "Groceries", "shared", 2, null],
];

const transactions: Transaction[] = rows.map(([d, description, amount_minor, category, allocation, account_id, member_id], i) => ({
    id: i + 1,
    account_id,
    import_id: 1,
    booked_on: day(d),
    description,
    amount_minor,
    currency: "SEK",
    allocation,
    member_id,
    category,
}));

const categories: Category[] = ["Groceries", "Eating out", "Home", "Transport", "Health", "Subscriptions", "Other"].map((name, i) => ({
    id: i + 1,
    name,
    is_fallback: name === "Other",
}));

const rules: CategoryRule[] = [
    { id: 1, pattern: "ICA", category: "Groceries" },
    { id: 2, pattern: "PELIKAN", category: "Eating out" },
    { id: 3, pattern: "ELLEVIO", category: "Home" },
];

const budget: BudgetMonth = {
    month,
    lines: [
        { category: "Groceries", recurring_minor: 6_000_00, override_minor: null, target_minor: 6_000_00, spent_minor: 3_940_75 },
        { category: "Eating out", recurring_minor: 1_500_00, override_minor: null, target_minor: 1_500_00, spent_minor: 1_604_00 },
        { category: "Home", recurring_minor: 2_500_00, override_minor: 4_000_00, target_minor: 4_000_00, spent_minor: 3_211_00 },
        { category: "Transport", recurring_minor: 1_200_00, override_minor: null, target_minor: 1_200_00, spent_minor: 1_010_00 },
        { category: "Subscriptions", recurring_minor: 700_00, override_minor: null, target_minor: 700_00, spent_minor: 638_00 },
        { category: "Health", recurring_minor: null, override_minor: null, target_minor: null, spent_minor: 214_90 },
        { category: "Other", recurring_minor: null, override_minor: null, target_minor: null, spent_minor: 0 },
    ],
    target_minor: 13_400_00,
    spent_minor: 10_618_65,
};

const summary: Summary = {
    ...budget,
    largest: transactions.filter((t) => t.amount_minor > 0).sort((a, b) => b.amount_minor - a.amount_minor).slice(0, 5),
    previous_spent_minor: 11_904_10,
};

const trend = [9_812, 11_240, 10_455, 12_980, 9_604, 10_877, 14_210, 11_096, 10_330, 12_118, 11_904, 10_618];
const trends: Trends = {
    months: trend.map((kr, i) => ({ month: addMonths(month, i - 11), spent_minor: kr * 100, by_category: {} })),
};

const settlement: Settlement = {
    household_id: 10,
    month,
    per_member: [
        { ...alex, amount_minor: 7_182_00, paid_minor: 9_838_40, balance_minor: 2_656_40 },
        { ...sam, amount_minor: 4_612_15, paid_minor: 1_955_75, balance_minor: -2_656_40 },
    ],
    transfers: [{ debtor: sam, creditor: alex, amount_minor: 2_656_40 }],
    outlay_minor: 1_495_00,
    shared_minor: 9_314_75,
    total_minor: 11_794_15,
    closed_at: null,
};

const history: Settlement[] = [1, 2].map((back, i) => ({
    ...settlement,
    month: addMonths(month, -back),
    transfers: [{ debtor: sam, creditor: alex, amount_minor: [1_904_00, 712_50][i] }],
    total_minor: [11_904_10, 12_118_00][i],
    closed_at: `${addMonths(month, -back + 1)}-02T09:00:00`,
}));

const imports: ImportResult[] = [
    {
        id: 1,
        account_id: 1,
        importer: "amex_se",
        filename: "activity.csv",
        period_start: day(1),
        period_end: day(28),
        transaction_count: 112,
        duplicate_count: 4,
        created_at: day(28),
    },
];

type Handler = (c: InternalAxiosRequestConfig) => unknown;
const routes: [string, RegExp, unknown][] = [
    ["get", /^\/me$/, me],
    ["get", /^\/accounts$/, accounts],
    ["get", /^\/transactions$/, ((c) => (c.params?.household_id ? transactions.filter((t) => t.account_id !== 3) : transactions)) as Handler],
    ["get", /^\/categories$/, categories],
    ["get", /^\/category-rules$/, rules],
    ["get", /^\/budgets$/, budget],
    ["get", /^\/summary$/, summary],
    ["get", /^\/trends$/, trends],
    ["get", /^\/households\/\d+$/, household],
    ["get", /^\/households\/\d+\/settlement$/, ((c) => history.find((h) => h.month === c.params?.month) ?? { ...settlement, month: c.params?.month }) as Handler],
    ["get", /^\/households\/\d+\/settlements$/, history],
    ["get", /^\/accounts\/\d+\/imports$/, ((c) => (c.url?.startsWith("/accounts/1/") ? imports : [])) as Handler],
];

/** Answers reads from the sample data; writes succeed and change nothing. */
export const demoAdapter: AxiosAdapter = async (config) => {
    const method = (config.method ?? "get").toLowerCase();
    const path = (config.url ?? "").split("?")[0];
    const route = routes.find(([m, re]) => m === method && re.test(path));
    const found = route ? route[2] : {};
    const data = typeof found === "function" ? (found as Handler)(config) : found;
    await new Promise((r) => setTimeout(r, 60));
    return { data: structuredClone(data), status: 200, statusText: "OK", headers: {}, config };
};
