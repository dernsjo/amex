import React, { useState, useRef } from "react";
import { uploadExpenses } from "../api";

const TransactionUploader = ({ onTransactionsLoaded }) => {
    const [isDragging, setIsDragging] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const fileInputRef = useRef(null);

    const handleFileUpload = async (files) => {
        if (!files || files.length === 0) return;
        const file = files[0];

        if (!file.name.endsWith(".csv")) {
            alert("Please upload a CSV file");
            return;
        }

        setIsProcessing(true);
        const success = await uploadExpenses(file);
        
        if (success) {
            alert("Expenses uploaded successfully");
            onTransactionsLoaded();
        } else {
            alert("Error uploading expenses. Please try again.");
        }
        setIsProcessing(false);
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        handleFileUpload(e.dataTransfer.files);
    };

    const openFileDialog = () => {
        fileInputRef.current?.click();
    };

    return (
        <div style={{ textAlign: "center", padding: "20px", border: "2px dashed gray", borderRadius: "10px" }}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}>
            <input
                type="file"
                ref={fileInputRef}
                style={{ display: "none" }}
                accept=".csv"
                onChange={(e) => handleFileUpload(e.target.files)}
            />
            <p>{isDragging ? "Drop the file here..." : "Drag & drop a CSV file here or click to select one"}</p>
            <button onClick={openFileDialog} disabled={isProcessing}>
                {isProcessing ? "Processing..." : "Select CSV File"}
            </button>
        </div>
    );
};

export default TransactionUploader;