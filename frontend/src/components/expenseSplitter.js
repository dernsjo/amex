import React, { useState } from "react";
import { calculateExpenseSplit } from "../api";

const ExpenseSplitter = ({ expenses }) => {
    const [splitResults, setSplitResults] = useState(null);

    const handleCalculateSplit = async () => {
        try {
            // Make sure expenses are passed correctly to the backend
            console.log("Calculating expense split for: ", expenses);
            
            const response = await calculateExpenseSplit(expenses); // Pass the expenses to the backend API
            setSplitResults(response);  // Update state with the backend response

            console.log("Calculation result: ", response);
        } catch (error) {
            console.error("Error calculating expense split:", error);
        }
    };

    return (
        <div>
            <button onClick={handleCalculateSplit}>Calculate Who Pays What</button>
            
            {splitResults && (
                <div>
                    <h3>Calculation Results</h3>
                    <ul>
                        {/* Display each user and their share */}
                        {Object.entries(splitResults.expenses).map(([user, amount]) => (
                            <li key={user}>{user}: {amount}</li>
                        ))}
                    </ul>
                    {/* Display other summary results */}
                    <p>Outlay: {splitResults.outlay}</p>
                    <p>Total Calculated: {splitResults.total}</p>
                    <p>Control (Total Expenses): {splitResults.control}</p>
                </div>
            )}
        </div>
    );
};

export default ExpenseSplitter;