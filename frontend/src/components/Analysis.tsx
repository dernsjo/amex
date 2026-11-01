import { useEffect, useState } from "react";
import { addMonths, errorMessage, getAnalysis, getTrends, kr, monthName, monthShort } from "../api";
import type { Analysis as AnalysisData, Transaction, Trends } from "../api";
import { MonthStepper, ShareBar, TREND_MONTHS, TrendBars, memberColor } from "./ui";

interface Props {
    householdId: number | null; // null: your own share of everything
    householdName?: string;
    month: string; // YYYY-MM
    onMonthChange: (month: string) => void;
    latestMonth: string | null; // the latest month anything counts toward
    transactions: Transaction[]; // only to know when spending changed
    categoriesVersion: number; // bumped when categories change
}

/** "+1 200,00 kr on Sep", "new this month", or nothing to compare. */
const change = (now: number, before: number, previousMonth: string) => {
    if (before === 0) return now > 0 ? "new this month" : "";
    if (now === 0) return `none, ${kr(before)} in ${monthShort(previousMonth)}`;
    const diff = now - before;
    if (diff === 0) return `same as ${monthShort(previousMonth)}`;
    return `${diff >= 0 ? "+" : "−"}${kr(Math.abs(diff))} on ${monthShort(previousMonth)}`;
};

/** Where a month's money went: per category against the month before, one category over a year, and per member. */
const Analysis = ({ householdId, householdName, month, onMonthChange, latestMonth, transactions, categoriesVersion }: Props) => {
    const [data, setData] = useState<AnalysisData | null>(null);
    const [trends, setTrends] = useState<Trends | null>(null);
    const [chosen, setChosen] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setError(null);
        Promise.all([getAnalysis(householdId, month), getTrends(householdId, addMonths(month, 1 - TREND_MONTHS), month)])
            .then(([a, t]) => {
                setData(a);
                setTrends(t);
            })
            .catch((e) => setError(errorMessage(e)));
    }, [householdId, month, transactions, categoriesVersion]);

    const previousMonth = addMonths(month, -1);
    const categories = data?.categories ?? [];
    const active = categories.filter((c) => c.spent_minor !== 0);
    // The category followed over the year: the one chosen, else this month's largest.
    const category =
        chosen && categories.some((c) => c.category === chosen) ? chosen : (active[0] ?? categories[0])?.category ?? null;
    const max = Math.max(1, ...categories.map((c) => c.spent_minor));
    const spent = data?.spent_minor ?? 0;
    const members = data?.members ?? [];
    const categoryTrend: Trends | null =
        trends && category
            ? { months: trends.months.map((m) => ({ ...m, spent_minor: m.by_category[category] ?? 0 })) }
            : null;

    return (
        <div className="view">
            <div className="view-head">
                <div>
                    <h1 className="head">Analysis</h1>
                    <p>
                        {householdName
                            ? `Spending shared in ${householdName}, by category and by person.`
                            : "Your own share: your personal spending plus your part of each household's shared spending."}
                    </p>
                </div>
                <MonthStepper month={month} onChange={onMonthChange} />
            </div>

            {error && (
                <p role="alert" className="alert">
                    {error}
                </p>
            )}

            {data && (
                <section className="block rise">
                    <div className="block-head">
                        <h2>Where it went in {monthName(month)}</h2>
                        <span className="small muted">
                            {kr(spent)}
                            {data.previous_spent_minor !== 0 && ` · ${change(spent, data.previous_spent_minor, previousMonth)}`}
                        </span>
                    </div>
                    {active.length === 0 ? (
                        <p className="muted">
                            Nothing counts toward {monthName(month)} yet.{" "}
                            {latestMonth && latestMonth !== month && (
                                <button className="link" onClick={() => onMonthChange(latestMonth)}>
                                    See {monthName(latestMonth)}
                                </button>
                            )}
                        </p>
                    ) : (
                        <ul className="cat-bars" aria-label="Spending per category">
                            {categories.map((c, i) => (
                                <li key={c.category}>
                                    <button
                                        type="button"
                                        className="cat-row"
                                        aria-pressed={c.category === category}
                                        onClick={() => setChosen(c.category)}
                                        style={{ ["--i" as string]: i }}
                                    >
                                        <span className="cat-name">{c.category}</span>
                                        <span className="cat-amount">{kr(c.spent_minor)}</span>
                                        <span className="cat-track" aria-hidden="true">
                                            <span
                                                className="cat-fill"
                                                style={{ width: `${(Math.max(0, c.spent_minor) / max) * 100}%` }}
                                            />
                                        </span>
                                        <span className="cat-meta">
                                            {spent > 0 && c.spent_minor > 0 && `${Math.round((c.spent_minor / spent) * 100)}% · `}
                                            {change(c.spent_minor, c.previous_minor, previousMonth)}
                                        </span>
                                    </button>
                                </li>
                            ))}
                        </ul>
                    )}
                </section>
            )}

            {categoryTrend && (
                <section className="block rise" style={{ ["--i" as string]: 1 }}>
                    <div className="block-head">
                        <h2>{category} over twelve months</h2>
                        <span className="small muted">Choose a category above, or a month below</span>
                    </div>
                    <TrendBars trends={categoryTrend} month={month} onSelect={onMonthChange} />
                </section>
            )}

            {members.length > 0 && active.length > 0 && (
                <section className="block rise" style={{ ["--i" as string]: 2 }}>
                    <div className="block-head">
                        <h2>Who carries what</h2>
                        <span className="small muted">Personal purchases plus each one's part of the shared</span>
                    </div>
                    <ShareBar
                        className="member-share grow-x"
                        parts={members.map((m, i) => ({
                            value: m.amount_minor,
                            color: memberColor(i),
                            label: m.display_name,
                            title: `${m.display_name}: ${kr(m.amount_minor)}`,
                        }))}
                    />
                    <div className="table-wrap">
                        <table className="table table-stack">
                            <thead>
                                <tr>
                                    <th>Category</th>
                                    {members.map((m, i) => (
                                        <th key={m.user_id} className="num">
                                            <span className="swatch" style={{ background: memberColor(i) }} />
                                            {m.display_name}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {categories
                                    .filter((c) => members.some((m) => m.by_category[c.category]))
                                    .map((c) => (
                                        <tr key={c.category}>
                                            <td style={{ fontWeight: 600 }}>{c.category}</td>
                                            {members.map((m) => (
                                                <td key={m.user_id} className="num" data-label={m.display_name}>
                                                    {kr(m.by_category[c.category] ?? 0)}
                                                </td>
                                            ))}
                                        </tr>
                                    ))}
                                <tr>
                                    <td style={{ fontWeight: 600 }}>Total</td>
                                    {members.map((m) => (
                                        <td key={m.user_id} className="num" data-label={m.display_name} style={{ fontWeight: 600 }}>
                                            {kr(m.amount_minor)}
                                        </td>
                                    ))}
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <p className="small muted">
                        Counts everything on the household's accounts, so purchases marked personal show here too, under
                        the person they belong to.
                    </p>
                </section>
            )}
        </div>
    );
};

export default Analysis;
