import { useRef, useState } from "react";
import type { DragEvent } from "react";
import { errorMessage, uploadExpenses } from "../api";

interface Props {
    onTransactionsLoaded: () => Promise<void>;
}

const TransactionUploader = ({ onTransactionsLoaded }: Props) => {
    const [isDragging, setIsDragging] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileUpload = async (files: FileList | null) => {
        if (!files || files.length === 0) return;
        const file = files[0];

        if (!file.name.toLowerCase().endsWith(".csv")) {
            setMessage("Please upload a CSV file");
            return;
        }

        setIsProcessing(true);
        setMessage(null);
        try {
            const imported = await uploadExpenses(file);
            setMessage(`Imported ${imported.length} transactions`);
            await onTransactionsLoaded();
        } catch (e) {
            setMessage(`Upload failed: ${errorMessage(e)}`);
        } finally {
            setIsProcessing(false);
            if (fileInputRef.current) fileInputRef.current.value = "";
        }
    };

    const handleDragOver = (e: DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDrop = (e: DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        handleFileUpload(e.dataTransfer.files);
    };

    return (
        <div
            style={{ textAlign: "center", padding: "20px", border: "2px dashed gray", borderRadius: "10px" }}
            onDragOver={handleDragOver}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
        >
            <input
                type="file"
                ref={fileInputRef}
                style={{ display: "none" }}
                accept=".csv"
                onChange={(e) => handleFileUpload(e.target.files)}
            />
            <p>{isDragging ? "Drop the file here..." : "Drag & drop an Amex CSV file here or click to select one"}</p>
            <button onClick={() => fileInputRef.current?.click()} disabled={isProcessing}>
                {isProcessing ? "Processing..." : "Select CSV File"}
            </button>
            {message && <p role="status">{message}</p>}
        </div>
    );
};

export default TransactionUploader;
