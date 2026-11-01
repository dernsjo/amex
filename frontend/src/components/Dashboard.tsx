import { useEffect, useState } from "react";
import { addMonths, errorMessage, getSummary, getTrends, kr, monthName } from "../api";
import type { Summary, Transaction, Trends } from "../api";

interface Props {
    householdId: number | null; // null: your own share of everything
    month: string; // YYYY-MM
    onMonthChange: (month: string) => void;
    transactions: Transaction[]; // only to know when spending changed
    categoriesVersion: number; // bumped when categories change
}

const TREND_MONTHS = 12;

/** Total spending per month as a line, ending at the selected month. */
const TrendLine = ({ trends, month, onSelect }: { trends: Trends; month: string; onSelect: (m: string) => void }) => {
    const width = 600;
    const height = 140;
    const pad = 24;
    const points = trends.months;
    const max = Math.max(1, ...points.map((p) => p.spent_minor));
    const x = (i: number) => pad + (i * (width - 2 * pad)) / Math.max(1, points.length - 1);
    const y = (v: number) => height - pad - (Math.max(0, v) * (height - 2 * pad)) / max;
    return (
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", maxWidth: `${width}px` }} role="img">
            <title>Spending per month</title>
            <line x1={pad} x2={width - pad} y1={height - pad} y2={height - pad} stroke="#ccc" />
            <polyline
                fill="none"
                stroke="#2980b9"
                strokeWidth={2}
                points={points.map((p, i) => `${x(i)},${y(p.spent_minor)}`).join(" ")}
            />
            {points.map((p, i) => (
                <g key={p.month} style={{ cursor: "pointer" }} onClick={() => onSelect(p.month)}>
                    <circle cx={x(i)} cy={y(p.spent_minor)} r={p.month === month ? 5 : 3} fill="#2980b9">
                        <title>{`${monthName(p.month)}: ${kr(p.spent_minor)}`}</title>
                    </circle>
                    <text x={x(i)} y={height - 6} fontSize="10" textAnchor="middle">
                        {p.month.slice(5)}
                    </text>
                </g>
            ))}
        </svg>
    );
};

/** A month at a glance: spending against target, the trend, and the largest spending. */
const Dashboard = ({ householdId, month, onMonthChange, transactions, categoriesVersion }: Props) => {
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

    const change = summary ? summary.spent_minor - summary.previous_spent_minor : 0;

    return (
        <div>
            <h3>
                <button onClick={() => onMonthChange(addMonths(month, -1))}>‹</button>{" "}
                <input type="month" value={month} onChange={(e) => e.target.value && onMonthChange(e.target.value)} />{" "}
                <button onClick={() => onMonthChange(addMonths(month, 1))}>›</button>
            </h3>
            {error && <p role="alert">{error}</p>}
            {summary && (
                <p>
                    {householdId ? "Shared spending" : "Your spending"} in {monthName(month)}:{" "}
                    <strong>{kr(summary.spent_minor)}</strong>
                    {summary.target_minor > 0 && <> of {kr(summary.target_minor)} budgeted</>}
                    {summary.previous_spent_minor !== 0 && (
                        <>
                            {" "}
                            ({change >= 0 ? "+" : "−"}
                            {kr(Math.abs(change))} from the month before)
                        </>
                    )}
                </p>
            )}
            {trends && <TrendLine trends={trends} month={month} onSelect={onMonthChange} />}
            {summary && summary.largest.length > 0 && (
                <>
                    <h4>Largest spending</h4>
                    <table style={{ margin: "0 auto" }}>
                        <tbody>
                            {summary.largest.map((t) => (
                                <tr key={t.id}>
                                    <td>{t.booked_on}</td>
                                    <td style={{ textAlign: "left" }}>{t.description}</td>
                                    <td>{t.category}</td>
                                    <td style={{ textAlign: "right" }}>{kr(t.amount_minor, t.currency)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </>
            )}
        </div>
    );
};

export default Dashboard;
