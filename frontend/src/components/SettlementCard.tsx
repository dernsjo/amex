import { useEffect, useState } from "react";
import { errorMessage, getSettlement } from "../api";
import type { Expense, Settlement } from "../api";

const kr = (amount: number) => amount.toLocaleString("sv-SE", { style: "currency", currency: "SEK" });

interface Props {
    expenses: Expense[];
}

const ExpenseSplitter = ({ expenses }: Props) => {
    const [result, setResult] = useState<Settlement | null>(null);
    const [error, setError] = useState<string | null>(null);

    // A result is stale as soon as the expenses change.
    useEffect(() => {
        setResult(null);
    }, [expenses]);

    const handleCalculateSplit = async () => {
        setError(null);
        try {
            setResult(await getSettlement());
        } catch (e) {
            setResult(null);
            setError(errorMessage(e));
        }
    };

    return (
        <div>
            <button onClick={handleCalculateSplit}>Calculate Who Pays What</button>
            {error && <p role="alert">{error}</p>}

            {result && (
                <div>
                    <h3>Calculation Results</h3>
                    <ul>
                        {Object.entries(result.per_member).map(([member, amount]) => (
                            <li key={member}>
                                {member}: {kr(amount)}
                            </li>
                        ))}
                    </ul>
                    <p>Outlay: {kr(result.outlay)}</p>
                    <p>Shared: {kr(result.shared)}</p>
                    <p>Total: {kr(result.total)}</p>
                </div>
            )}
        </div>
    );
};

export default ExpenseSplitter;
