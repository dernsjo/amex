import { useCallback, useEffect, useRef, useState } from "react";
import type { DragEvent } from "react";
import { confirmImport, errorMessage, getImports, kr, previewImport, undoImport } from "../api";
import type { Account, ImportConfig, ImportPreview, ImportResult } from "../api";
import AccountSelect from "./AccountSelect";
import MappingForm from "./MappingForm";
import type { MappingDraft } from "./MappingForm";

interface Props {
    accounts: Account[]; // the user's own accounts
    onImported: () => Promise<void>;
}

const SOURCE_TEXT: Record<ImportPreview["source"], string> = {
    requested: "Read with the settings below.",
    saved: "Read the same way as this account's last import.",
    detected: "Recognized the file format.",
    guessed: "Guessed which columns to use: check the preview before importing.",
    none: "Couldn't tell how to read this file: choose the columns below.",
};

/** Rows shown in the preview; the counts cover the whole file. */
const PREVIEW_ROWS = 50;

const isComplete = (m: MappingDraft) => Boolean(m.date_column && m.description_column && m.amount_column);

/** Upload → preview (and fix the column mapping if needed) → confirm. */
const ImportWizard = ({ accounts, onImported }: Props) => {
    const [accountId, setAccountId] = useState<number | null>(null);
    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<ImportPreview | null>(null);
    const [importer, setImporter] = useState("csv");
    const [mapping, setMapping] = useState<MappingDraft | null>(null);
    const [history, setHistory] = useState<ImportResult[]>([]);
    const [busy, setBusy] = useState(false);
    const [isDragging, setIsDragging] = useState(false);
    const [message, setMessage] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const latestPreview = useRef(0); // ignore answers to previews that were superseded

    const selected = accountId ?? accounts[0]?.id ?? null;

    const fetchHistory = useCallback(async () => {
        setHistory(selected === null ? [] : await getImports(selected));
    }, [selected]);

    useEffect(() => {
        fetchHistory().catch((e) => setMessage(errorMessage(e)));
    }, [fetchHistory]);

    const reset = () => {
        setFile(null);
        setPreview(null);
        setMapping(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    const runPreview = async (f: File, config?: ImportConfig) => {
        if (selected === null) return;
        const request = ++latestPreview.current;
        setBusy(true);
        setMessage(null);
        try {
            const result = await previewImport(selected, f, config);
            if (request !== latestPreview.current) return;
            setPreview(result);
            if (!config) {
                // First look at the file: start from what the server chose or guessed.
                setImporter(result.config?.importer ?? "csv");
                const m = result.config?.mapping ?? result.suggested_mapping;
                setMapping({
                    ...m,
                    date_column: m.date_column ?? "",
                    description_column: m.description_column ?? "",
                    amount_column: m.amount_column ?? "",
                });
            }
        } catch (e) {
            if (request === latestPreview.current) {
                setPreview(null);
                setMessage(errorMessage(e));
            }
        } finally {
            if (request === latestPreview.current) setBusy(false);
        }
    };

    /** The config the preview on screen was made with, or undefined if the mapping isn't complete yet. */
    const currentConfig = (): ImportConfig | undefined => {
        if (importer !== "csv") return { importer, mapping: null };
        return mapping && isComplete(mapping) ? { importer, mapping } : undefined;
    };

    const handleFile = (files: FileList | null) => {
        const f = files?.[0];
        if (!f) return;
        if (!f.name.toLowerCase().endsWith(".csv")) {
            setMessage("Please upload a CSV file");
            return;
        }
        setFile(f);
        runPreview(f);
    };

    const handleImporter = (id: string) => {
        setImporter(id);
        if (!file) return;
        if (id !== "csv") runPreview(file, { importer: id, mapping: null });
        else if (mapping && isComplete(mapping)) runPreview(file, { importer: id, mapping });
    };

    const handleMapping = (m: MappingDraft) => {
        setMapping(m);
        if (file && isComplete(m)) runPreview(file, { importer: "csv", mapping: m });
    };

    const handleConfirm = async () => {
        if (!file || selected === null) return;
        setBusy(true);
        try {
            const result = await confirmImport(selected, file, currentConfig());
            const skipped = result.duplicate_count ? ` (${result.duplicate_count} already imported)` : "";
            setMessage(`Imported ${result.transaction_count} transactions${skipped}`);
            reset();
            await Promise.all([fetchHistory(), onImported()]);
        } catch (e) {
            setMessage(`Import failed: ${errorMessage(e)}`);
        } finally {
            setBusy(false);
        }
    };

    const handleUndo = async (imp: ImportResult) => {
        if (selected === null) return;
        if (!window.confirm(`Remove ${imp.filename} and its ${imp.transaction_count} transactions?`)) return;
        try {
            await undoImport(selected, imp.id);
            await Promise.all([fetchHistory(), onImported()]);
        } catch (e) {
            setMessage(errorMessage(e));
        }
    };

    const handleDrop = (e: DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        handleFile(e.dataTransfer.files);
    };

    if (accounts.length === 0) return <p>Add an account to import transactions.</p>;

    return (
        <div style={{ padding: "20px", border: "2px dashed gray", borderRadius: "10px" }}>
            <h2>Import</h2>
            <AccountSelect
                accounts={accounts}
                value={selected}
                onChange={(id) => {
                    setAccountId(id);
                    reset();
                }}
            />

            {!preview && (
                <div
                    onDragOver={(e) => {
                        e.preventDefault();
                        setIsDragging(true);
                    }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={handleDrop}
                >
                    <input
                        type="file"
                        ref={fileInputRef}
                        style={{ display: "none" }}
                        accept=".csv"
                        onChange={(e) => handleFile(e.target.files)}
                    />
                    <p>{isDragging ? "Drop the file here..." : "Drag & drop a bank CSV export here or click to select one"}</p>
                    <button onClick={() => fileInputRef.current?.click()} disabled={busy}>
                        {busy ? "Reading..." : "Select CSV File"}
                    </button>
                </div>
            )}

            {preview && (
                <div>
                    <p>
                        <strong>{preview.filename}</strong>: {SOURCE_TEXT[preview.source]}
                    </p>
                    {preview.already_imported_at && (
                        <p role="status">
                            This exact file was already imported on{" "}
                            {new Date(preview.already_imported_at).toLocaleDateString("sv-SE")}.
                        </p>
                    )}
                    <label>
                        Read as{" "}
                        <select value={importer} onChange={(e) => handleImporter(e.target.value)}>
                            {preview.importers.map((i) => (
                                <option key={i.id} value={i.id}>
                                    {i.name}
                                </option>
                            ))}
                        </select>
                    </label>
                    {importer === "csv" && mapping && (
                        <MappingForm preview={preview} mapping={mapping} onChange={handleMapping} />
                    )}
                    {preview.error && <p role="alert">{preview.error}</p>}

                    {preview.transactions.length > 0 && (
                        <>
                            <p>
                                {preview.new_count} new
                                {preview.duplicate_count > 0 && `, ${preview.duplicate_count} already imported (skipped)`}
                            </p>
                            <table border={1} style={{ width: "100%", borderCollapse: "collapse" }}>
                                <thead>
                                    <tr>
                                        <th>Date</th>
                                        <th>Description</th>
                                        <th>Category</th>
                                        <th>Amount</th>
                                        <th />
                                    </tr>
                                </thead>
                                <tbody>
                                    {preview.transactions.slice(0, PREVIEW_ROWS).map((t, i) => (
                                        <tr key={i} style={t.duplicate ? { opacity: 0.5 } : undefined}>
                                            <td>{t.booked_on}</td>
                                            <td>{t.description}</td>
                                            <td>{t.category}</td>
                                            <td style={{ textAlign: "right" }}>{kr(t.amount_minor)}</td>
                                            <td>{t.duplicate ? "already imported" : "new"}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {preview.transactions.length > PREVIEW_ROWS && (
                                <p>…and {preview.transactions.length - PREVIEW_ROWS} more</p>
                            )}
                        </>
                    )}

                    <button
                        onClick={handleConfirm}
                        disabled={busy || !!preview.error || preview.new_count === 0 || !currentConfig()}
                    >
                        Import {preview.new_count} transactions
                    </button>
                    <button onClick={reset} disabled={busy}>
                        Cancel
                    </button>
                </div>
            )}

            {message && <p role="status">{message}</p>}

            {history.length > 0 && (
                <details>
                    <summary>Previous imports ({history.length})</summary>
                    <ul style={{ listStyle: "none", padding: 0 }}>
                        {history.map((imp) => (
                            <li key={imp.id}>
                                {imp.filename}: {imp.period_start} – {imp.period_end}, {imp.transaction_count}{" "}
                                transactions <button onClick={() => handleUndo(imp)}>Undo</button>
                            </li>
                        ))}
                    </ul>
                </details>
            )}
        </div>
    );
};

export default ImportWizard;
