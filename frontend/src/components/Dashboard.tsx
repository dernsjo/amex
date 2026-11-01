import { useEffect, useState } from "react";
import { addMonths, dayName, errorMessage, getSettlement, getSummary, getTrends, kr, monthName, monthShort } from "../api";
import type { Settlement, Summary, Transaction, Trends } from "../api";
import type { View } from "../App";
import { MonthStepper, ShareBar } from "./ui";

interface Props {
    householdId: number | null; // null: your own share of everything
    householdName?: string;
    month: string; // YYYY-MM
    onMonthChange: (month: string) => void;
    transactions: Transaction[]; // only to know when spending changed
    categoriesVersion: number; // bumped when categories change
    hasAccounts: boolean;
    onGo: (view: View) => void;
}

const TREND_MONTHS = 12;

/** Twelve months of spending as bars; the chosen month in the accent. Choosing a bar moves the whole view. */
const TrendBars = ({ trends, month, onSelect }: { trends: Trends; month: string; onSelect: (m: string) => void }) => {
    const max = Math.max(1, ...trends.months.map((p) => p.spent_minor));
    return (
        <div className="trend">
            <div className="trend-bars" role="group" aria-label="Spending per month">
                {trends.months.map((p, i) => {
                    const h = `${(Math.max(0, p.spent_minor) / max) * 100}%`;
                    return (
                        <button
                            key={p.month}
                            type="button"
                            className={`trend-bar${i < 2 ? " edge-start" : i >= trends.months.length - 2 ? " edge-end" : ""}`}
                            aria-pressed={p.month === month}
                            aria-label={`${monthName(p.month)}: ${kr(p.spent_minor)}`}
                            onClick={() => onSelect(p.month)}
                            style={{ ["--i" as string]: i, ["--h" as string]: `calc((14rem - 1.65rem) * ${Math.max(0, p.spent_minor) / max})` }}
                        >
                            <span className="tip">
                                {monthShort(p.month)} {kr(p.spent_minor)}
                            </span>
                            <span className="bar" style={{ height: `calc(${h} - 1.65rem)` }} />
                            <span className="m">{monthShort(p.month).slice(0, 1)}</span>
                        </button>
                    );
                })}
            </div>
        </div>
    );
};

/** The household's verdict for the month, as one sentence on a field. */
const SettleTile = ({ householdId, month, onGo }: { householdId: number; month: string; onGo: (v: View) => void }) => {
    const [result, setResult] = useState<Settlement | null>(null);
    useEffect(() => {
        getSettlement(householdId, month)
            .then(setResult)
            .catch(() => setResult(null));
    }, [householdId, month]);
    if (!result) return null;
    const [first] = result.transfers;
    return (
        <section className="tile tile-2 rise" style={{ ["--i" as string]: 2 }} aria-labelledby="settle-tile">
            <p id="settle-tile" className="head">
                {first ? (
                    <>
                        {first.debtor.display_name} pays {first.creditor.display_name} {kr(first.amount_minor)}
                    </>
                ) : (
                    "Everyone is even."
                )}
            </p>
            <p>
                {result.transfers.length > 1 && `And ${result.transfers.length - 1} more transfer(s). `}
                Shared spending in {monthName(month)}: {kr(result.shared_minor)}.
                {result.closed_at ? " This month is closed." : " Nothing is final until you close the month."}
            </p>
            <div>
                <button className="btn btn-ink" onClick={() => onGo("settle")}>
                    See the settlement
                </button>
            </div>
        </section>
    );
};

/** A month at a glance: spending against target, the trend, and the largest spending. */
const Dashboard = ({ householdId, householdName, month, onMonthChange, transactions, categoriesVersion, hasAccounts, onGo }: Props) => {
    const [summary, setSummary] = useState<Summary | null>(null);
    const [trends, setTrends] = useState<Trends | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setError(null);
        Promise.all([getSummary(householdId, month), getTrends(householdId, addMonths(month, 1 - TREND_MONTHS), month)])
            .then(([s, t]) => {
                setSummary(s);
                setTrends(t);
            })
            .catch((e) => setError(errorMessage(e)));
    }, [householdId, month, transactions, categoriesVersion]);

    if (!hasAccounts)
        return (
            <div className="view">
                <div className="tile tile-2 rise" style={{ minHeight: "60svh", alignContent: "end" }}>
                    <h1 className="display">Start with one statement.</h1>
                    <p className="lead">Add the account your card or bank belongs to, then import its CSV export.</p>
                    <div>
                        <button className="btn btn-primary" onClick={() => onGo("import")}>
                            Import a statement
                        </button>
                    </div>
                </div>
            </div>
        );

    const change = summary ? summary.spent_minor - summary.previous_spent_minor : 0;
    const target = summary?.target_minor ?? 0;
    const spent = summary?.spent_minor ?? 0;
    const whose = householdName ? `shared in ${householdName}` : "spent by you";

    return (
        <div className="view">
            <div className="view-head">
                <MonthStepper month={month} onChange={onMonthChange} />
            </div>

            {error && (
                <p role="alert" className="alert">
                    {error}
                </p>
            )}

            {summary && (
                <section className="total tile tile-1" aria-labelledby="total-figure">
                    <div className="rise">
                        <h1 id="total-figure" className="total-figure">
                            {kr(spent)}
                        </h1>
                        <p className="lead">
                            {whose} in {monthName(month)}
                        </p>
                    </div>
                    <div className="total-meta rise" style={{ ["--i" as string]: 1 }}>
                        {target > 0 ? (
                            <span>
                                {spent <= target ? `${kr(target - spent)} left of ${kr(target)}` : `${kr(spent - target)} over a budget of ${kr(target)}`}
                            </span>
                        ) : (
                            <button className="link" onClick={() => onGo("budget")}>
                                Set a budget
                            </button>
                        )}
                        {summary.previous_spent_minor !== 0 && (
                            <span>
                                {change >= 0 ? "+" : "−"}
                                {kr(Math.abs(change))} on {monthName(addMonths(month, -1))}
                            </span>
                        )}
                    </div>
                    {target > 0 && (
                        <div className="rise" style={{ ["--i" as string]: 2, display: "grid", gap: "0.6rem" }}>
                            <ShareBar
                                className="grow-x"
                                parts={[
                                    { value: Math.min(spent, target), className: "spent", title: `Spent ${kr(spent)}` },
                                    { value: Math.max(0, target - spent), className: "rest", title: "Left" },
                                    { value: Math.max(0, spent - target), className: "over", title: "Over budget" },
                                ]}
                            />
                            <div className="share-legend">
                                <span className="key">Spent</span>
                                {spent > target ? (
                                    <span className="key" style={{ ["--key" as string]: "var(--accent)" }}>
                                        Over budget
                                    </span>
                                ) : (
                                    <span className="key" style={{ ["--key" as string]: "var(--bg)" }}>
                                        Left to spend
                                    </span>
                                )}
                            </div>
                        </div>
                    )}
                </section>
            )}

            {householdId !== null && <SettleTile householdId={householdId} month={month} onGo={onGo} />}

            <div className="cols">
                {trends && (
                    <section className="block span-7 rise" style={{ ["--i" as string]: 3 }}>
                        <div className="block-head">
                            <h2>The last twelve months</h2>
                            <span className="small muted">Choose a month to look at it</span>
                        </div>
                        <TrendBars trends={trends} month={month} onSelect={onMonthChange} />
                    </section>
                )}
                {summary && (
                    <section className="block span-5 rise" style={{ ["--i" as string]: 4 }}>
                        <div className="block-head">
                            <h2>Largest spending</h2>
                            <button className="link small" onClick={() => onGo("transactions")}>
                                All transactions
                            </button>
                        </div>
                        {summary.largest.length === 0 ? (
                            <p className="muted">Nothing spent in {monthName(month)} yet.</p>
                        ) : (
                            <ul className="list">
                                {summary.largest.map((t) => (
                                    <li key={t.id} className="list-row">
                                        <span className="desc">{t.description}</span>
                                        <span className="amount">{kr(t.amount_minor, t.currency)}</span>
                                        <span className="sub">
                                            {dayName(t.booked_on)} · {t.category ?? "Uncategorized"}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </section>
                )}
            </div>
        </div>
    );
};

export default Dashboard;
