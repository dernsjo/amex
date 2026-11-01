import { useCallback, useEffect, useState } from "react";
import { closeMonth, errorMessage, getSettlement, getSettlements, kr, monthName, reopenMonth } from "../api";
import type { Settlement, Transaction } from "../api";

interface Props {
    householdId: number;
    month: string; // YYYY-MM
    isOwner: boolean; // only owners can reopen a closed month
    transactions: Transaction[]; // only to know when spending changed
}

/** Who owes whom for one month, closing the month, and the months closed before. */
const SettlementCard = ({ householdId, month, isOwner, transactions }: Props) => {
    const [result, setResult] = useState<Settlement | null>(null);
    const [history, setHistory] = useState<Settlement[]>([]);
    const [error, setError] = useState<string | null>(null);

    const fetchSettlement = useCallback(async () => {
        setError(null);
        setResult(null);
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

    const handleClose = () => {
        if (window.confirm(`Close ${monthName(month)}? Its settlement is stored as it is now; later changes won't affect it.`))
            change(() => closeMonth(householdId, month));
    };

    const handleReopen = () => {
        if (window.confirm(`Reopen ${monthName(month)}? Its settlement will be worked out from the transactions again.`))
            change(() => reopenMonth(householdId, month));
    };

    return (
        <div>
            <h3>Who owes whom: {monthName(month)}</h3>
            {error && <p role="alert">{error}</p>}

            {result && (
                <div>
                    {result.transfers.length === 0 ? (
                        <p>Everyone is even.</p>
                    ) : (
                        <ul style={{ listStyle: "none", padding: 0 }}>
                            {result.transfers.map((t) => (
                                <li key={`${t.debtor.user_id}-${t.creditor.user_id}`}>
                                    <strong>{t.debtor.display_name}</strong> pays{" "}
                                    <strong>{t.creditor.display_name}</strong> {kr(t.amount_minor)}
                                </li>
                            ))}
                        </ul>
                    )}
                    <table style={{ margin: "0 auto" }}>
                        <thead>
                            <tr>
                                <th />
                                <th title="Personal spending plus their part of shared">Responsible for</th>
                                <th title="Spending on accounts they own">Paid</th>
                                <th>Balance</th>
                            </tr>
                        </thead>
                        <tbody>
                            {result.per_member.map((m) => (
                                <tr key={m.user_id}>
                                    <td>{m.display_name}</td>
                                    <td>{kr(m.amount_minor)}</td>
                                    <td>{kr(m.paid_minor)}</td>
                                    <td>{kr(m.balance_minor)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    <p>
                        Shared: {kr(result.shared_minor)} · Outlays: {kr(result.outlay_minor)} · Total:{" "}
                        {kr(result.total_minor)}
                    </p>
                    {result.closed_at ? (
                        <p>
                            Closed {new Date(result.closed_at).toLocaleDateString("sv-SE")}.{" "}
                            {isOwner && <button onClick={handleReopen}>Reopen</button>}
                        </p>
                    ) : (
                        <button onClick={handleClose}>Close {monthName(month)}</button>
                    )}
                </div>
            )}

            {history.length > 0 && (
                <>
                    <h4>Closed months</h4>
                    <ul style={{ listStyle: "none", padding: 0 }}>
                        {history.map((s) => (
                            <li key={s.month}>
                                {monthName(s.month)}:{" "}
                                {s.transfers.length === 0
                                    ? "even"
                                    : s.transfers
                                          .map((t) => `${t.debtor.display_name} → ${t.creditor.display_name} ${kr(t.amount_minor)}`)
                                          .join(", ")}
                            </li>
                        ))}
                    </ul>
                </>
            )}
        </div>
    );
};

export default SettlementCard;
