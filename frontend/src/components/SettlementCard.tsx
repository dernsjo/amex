import { useEffect, useState } from "react";
import { errorMessage, getSettlement, kr } from "../api";
import type { Settlement, Transaction } from "../api";

interface Props {
    householdId: number;
    transactions: Transaction[];
}

const SettlementCard = ({ householdId, transactions }: Props) => {
    const [result, setResult] = useState<Settlement | null>(null);
    const [error, setError] = useState<string | null>(null);

    // A result is stale as soon as the transactions or the household change.
    useEffect(() => {
        setResult(null);
    }, [transactions, householdId]);

    const handleCalculate = async () => {
        setError(null);
        try {
            setResult(await getSettlement(householdId));
        } catch (e) {
            setResult(null);
            setError(errorMessage(e));
        }
    };

    return (
        <div>
            <button onClick={handleCalculate}>Calculate Who Pays What</button>
            {error && <p role="alert">{error}</p>}

            {result && (
                <div>
                    <h3>Calculation Results</h3>
                    <ul>
                        {result.per_member.map((m) => (
                            <li key={m.user_id}>
                                {m.display_name}: {kr(m.amount_minor)}
                            </li>
                        ))}
                    </ul>
                    <p>Outlay: {kr(result.outlay_minor)}</p>
                    <p>Shared: {kr(result.shared_minor)}</p>
                    <p>Total: {kr(result.total_minor)}</p>
                </div>
            )}
        </div>
    );
};

export default SettlementCard;
