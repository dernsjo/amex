import { useCallback, useEffect, useState } from "react";
import { closeMonth, errorMessage, getSettlement, getSettlements, kr, monthName, reopenMonth } from "../api";
import type { Settlement, Transaction } from "../api";
import { MonthStepper, ShareBar, memberColor, useDialogs } from "./ui";

interface Props {
    householdId: number;
    householdName: string;
    month: string; // YYYY-MM
    onMonthChange: (month: string) => void;
    isOwner: boolean; // only owners can reopen a closed month
    transactions: Transaction[]; // only to know when spending changed
}

/** Who owes whom for one month, closing the month, and the months closed before. */
const SettlementCard = ({ householdId, householdName, month, onMonthChange, isOwner, transactions }: Props) => {
    const dialogs = useDialogs();
    const [result, setResult] = useState<Settlement | null>(null);
    const [history, setHistory] = useState<Settlement[]>([]);
    const [error, setError] = useState<string | null>(null);

    const fetchSettlement = useCallback(async () => {
        setError(null);
        try {
            const [current, closed] = await Promise.all([getSettlement(householdId, month), getSettlements(householdId)]);
            setResult(current);
            setHistory(closed);
        } catch (e) {
            setError(errorMessage(e));
        }
    }, [householdId, month]);

    useEffect(() => {
        fetchSettlement();
    }, [fetchSettlement, transactions]);

    const change = async (action: () => Promise<unknown>) => {
        try {
            await action();
            await fetchSettlement();
        } catch (e) {
            setError(errorMessage(e));
        }
    };

    const handleClose = async () => {
        if (
            await dialogs.confirm(
                `Close ${monthName(month)}?`,
                "Its settlement is stored as it is now; later changes to its transactions won't affect it.",
                "Close the month",
            )
        )
            change(() => closeMonth(householdId, month));
    };

    const handleReopen = async () => {
        if (
            await dialogs.confirm(
                `Reopen ${monthName(month)}?`,
                "Its settlement will be worked out from the transactions again.",
                "Reopen",
            )
        )
            change(() => reopenMonth(householdId, month));
    };

    const colorOf = (userId: number) => memberColor(Math.max(0, result?.per_member.findIndex((m) => m.user_id === userId) ?? 0));

    return (
        <div className="view">
            <div className="view-head">
                <div>
                    <h1 className="lead">Settle up in {householdName}</h1>
                </div>
                <MonthStepper month={month} onChange={onMonthChange} />
            </div>

            {error && (
                <p role="alert" className="alert">
                    {error}
                </p>
            )}

            {result && (
                <>
                    <section className="verdict" aria-label="Who owes whom">
                        {result.transfers.length === 0 ? (
                            <p className="display rise">Everyone is even.</p>
                        ) : (
                            <ul className="verdict" style={{ listStyle: "none", padding: 0 }}>
                                {result.transfers.map((t, i) => (
                                    <li
                                        key={`${t.debtor.user_id}-${t.creditor.user_id}`}
                                        className="transfer rise"
                                        style={{ ["--i" as string]: i }}
                                    >
                                        {t.debtor.display_name} pays {t.creditor.display_name}{" "}
                                        <span className="amt">{kr(t.amount_minor)}</span>
                                    </li>
                                ))}
                            </ul>
                        )}
                        <div className="row">
                            {result.closed_at ? (
                                <>
                                    <p className="tag" style={{ background: "var(--field-2)" }}>
                                        Closed {new Date(result.closed_at).toLocaleDateString("en-GB")}
                                    </p>
                                    {isOwner && (
                                        <button className="btn btn-small" onClick={handleReopen}>
                                            Reopen {monthName(month)}
                                        </button>
                                    )}
                                </>
                            ) : (
                                <button className="btn btn-primary" onClick={handleClose}>
                                    Close {monthName(month)}
                                </button>
                            )}
                        </div>
                    </section>

                    <section className="block rise" style={{ ["--i" as string]: 2 }}>
                        <div className="block-head">
                            <h2>Who carries what</h2>
                            <span className="small muted">Personal spending plus each one's part of the shared</span>
                        </div>
                        <ShareBar
                            className="member-share grow-x"
                            parts={result.per_member.map((m, i) => ({
                                value: m.amount_minor,
                                color: memberColor(i),
                                label: m.display_name,
                                title: `${m.display_name}: ${kr(m.amount_minor)}`,
                            }))}
                        />
                        <dl className="figures">
                            <div>
                                <dt>Shared</dt>
                                <dd>{kr(result.shared_minor)}</dd>
                            </div>
                            <div>
                                <dt>Outlays</dt>
                                <dd>{kr(result.outlay_minor)}</dd>
                            </div>
                            <div>
                                <dt>Total</dt>
                                <dd>{kr(result.total_minor)}</dd>
                            </div>
                        </dl>
                        <div className="table-wrap">
                            <table className="table table-stack">
                                <thead>
                                    <tr>
                                        <th>Member</th>
                                        <th className="num">Responsible for</th>
                                        <th className="num">Paid</th>
                                        <th className="num">Balance</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {result.per_member.map((m) => (
                                        <tr key={m.user_id}>
                                            <td style={{ fontWeight: 600 }}>
                                                <span className="swatch" style={{ background: colorOf(m.user_id) }} />
                                                {m.display_name}
                                            </td>
                                            <td className="num" data-label="Responsible for">
                                                {kr(m.amount_minor)}
                                            </td>
                                            <td className="num" data-label="Paid">
                                                {kr(m.paid_minor)}
                                            </td>
                                            <td data-label="Balance" className={`num ${m.balance_minor < 0 ? "balance-neg" : "balance-pos"}`}>
                                                {m.balance_minor > 0 && "+"}
                                                {kr(m.balance_minor)}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <p className="small muted">
                            A positive balance is owed money; a negative one owes. Paid counts spending on accounts each
                            member owns.
                        </p>
                    </section>
                </>
            )}

            {history.length > 0 && (
                <section className="block">
                    <div className="block-head">
                        <h2>Closed months</h2>
                    </div>
                    <ul className="list">
                        {history.map((s) => (
                            <li key={s.month} className="list-row">
                                <button className="desc link" style={{ textAlign: "left" }} onClick={() => onMonthChange(s.month)}>
                                    {monthName(s.month)}
                                </button>
                                <span className="amount">{kr(s.total_minor)}</span>
                                <span className="sub">
                                    {s.transfers.length === 0
                                        ? "Everyone was even"
                                        : s.transfers
                                              .map((t) => `${t.debtor.display_name} paid ${t.creditor.display_name} ${kr(t.amount_minor)}`)
                                              .join(" · ")}
                                </span>
                            </li>
                        ))}
                    </ul>
                </section>
            )}
        </div>
    );
};

export default SettlementCard;
