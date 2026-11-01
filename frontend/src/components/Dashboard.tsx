import { useEffect, useState } from "react";
import { addMonths, dayName, errorMessage, getSettlement, getSummary, getTrends, kr, monthName } from "../api";
import type { Settlement, Summary, Transaction, Trends } from "../api";
import type { View } from "../App";
import { MonthStepper, ShareBar, TREND_MONTHS, TrendBars } from "./ui";

interface Props {
    householdId: number | null; // null: your own share of everything
    householdName?: string;
    month: string; // YYYY-MM
    onMonthChange: (month: string) => void;
    transactions: Transaction[]; // only to know when spending changed
    categoriesVersion: number; // bumped when categories change
    hasAccounts: boolean;
    latestMonth: string | null; // the latest month anything counts toward
    onGo: (view: View) => void;
}


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
    // Card bills first: nobody has paid them yet, so what each pays is the headline.
    const [bill] = result.bills ?? [];
    const billShares = bill?.shares.filter((s) => s.amount_minor !== 0) ?? [];
    const more = (result.bills?.length ?? 0) - (bill ? 1 : 0) + result.transfers.length - (bill ? 0 : first ? 1 : 0);
    return (
        <section className="tile tile-2 rise" style={{ ["--i" as string]: 2 }} aria-labelledby="settle-tile">
            <p id="settle-tile" className="head">
                {bill ? (
                    <>
                        {bill.account_name} bill:{" "}
                        {billShares.map((s) => `${s.display_name} pays ${kr(s.amount_minor)}`).join(", ")}
                    </>
                ) : first ? (
                    <>
                        {first.debtor.display_name} pays {first.creditor.display_name} {kr(first.amount_minor)}
                    </>
                ) : (
                    "Everyone is even."
                )}
            </p>
            <p>
                {more > 0 && `And ${more} more to settle. `}
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
const Dashboard = ({ householdId, householdName, month, onMonthChange, transactions, categoriesVersion, hasAccounts, latestMonth, onGo }: Props) => {
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
                        {spent === 0 && summary.largest.length === 0 && latestMonth && latestMonth !== month && (
                            <p>
                                Nothing counts toward {monthName(month)} yet.{" "}
                                <button className="link" onClick={() => onMonthChange(latestMonth)}>
                                    See {monthName(latestMonth)}
                                </button>
                            </p>
                        )}
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
