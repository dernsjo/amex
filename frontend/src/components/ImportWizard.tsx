import { useCallback, useEffect, useRef, useState } from "react";
import type { DragEvent } from "react";
import {
    confirmImport,
    dayName,
    errorMessage,
    getImports,
    kr,
    monthName,
    previewImport,
    undoImport,
    updateImport,
} from "../api";
import type { Account, ImportConfig, ImportPreview, ImportResult } from "../api";
import MappingForm from "./MappingForm";
import type { MappingDraft } from "./MappingForm";
import { Segmented, useDialogs } from "./ui";

interface Props {
    accounts: Account[]; // the user's own accounts
    onImported: () => Promise<void>;
    onAddAccount: () => void;
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
const ImportWizard = ({ accounts, onImported, onAddAccount }: Props) => {
    const dialogs = useDialogs();
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
        const ok = await dialogs.confirm(`Undo ${imp.filename}?`, `Its ${imp.transaction_count} transactions are removed.`, "Undo import");
        if (!ok) return;
        try {
            await undoImport(selected, imp.id);
            await Promise.all([fetchHistory(), onImported()]);
        } catch (e) {
            setMessage(errorMessage(e));
        }
    };

    const handlePeriod = async (imp: ImportResult, period: string) => {
        if (selected === null || period === imp.period) return;
        try {
            await updateImport(selected, imp.id, period);
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

    const head = (
        <div className="view-head">
            <div>
                <h1 className="head">Import</h1>
                <p>Bring in a bank or card statement as a CSV export. Nothing is saved until you confirm.</p>
            </div>
        </div>
    );

    if (accounts.length === 0)
        return (
            <div className="view">
                {head}
                <div className="empty">
                    <p className="lead">Statements belong to an account.</p>
                    <p>Add the card or bank account first, then import its exports here.</p>
                    <button className="btn btn-primary" onClick={onAddAccount}>
                        Add an account
                    </button>
                </div>
            </div>
        );

    const account = accounts.find((a) => a.id === selected);

    return (
        <div className="view">
            {head}

            <section className="block">
                <div className="block-head">
                    <h2>Into which account?</h2>
                </div>
                <Segmented
                    label="Account"
                    value={String(selected ?? "")}
                    onChange={(id) => {
                        setAccountId(Number(id));
                        reset();
                    }}
                    options={accounts.map((a) => ({ value: String(a.id), label: a.name }))}
                />
            </section>

            {message && (
                <p role="status" className="status">
                    {message}
                </p>
            )}

            {!preview && (
                <div
                    className={`drop rise${isDragging ? " dragging" : ""}`}
                    onDragOver={(e) => {
                        e.preventDefault();
                        setIsDragging(true);
                    }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                >
                    <div className="drop-motif" aria-hidden="true">
                        <span />
                        <span />
                        <span />
                        <span />
                        <span />
                    </div>
                    <input
                        type="file"
                        ref={fileInputRef}
                        className="sr-only"
                        accept=".csv"
                        tabIndex={-1}
                        onChange={(e) => handleFile(e.target.files)}
                    />
                    <p className="head">
                        {isDragging ? "Let go to read it." : `Drop a statement for ${account?.name ?? "this account"}.`}
                    </p>
                    <p>
                        {account?.import_config
                            ? "It will be read the same way as the last one."
                            : "Amex exports are recognized; any other bank's CSV can be mapped column by column."}
                    </p>
                    <button
                        type="button"
                        className="btn btn-ink"
                        disabled={busy}
                        onClick={(e) => {
                            e.stopPropagation();
                            fileInputRef.current?.click();
                        }}
                    >
                        {busy ? "Reading…" : "Choose a CSV file"}
                    </button>
                </div>
            )}

            {preview && (
                <section className="block">
                    <div className="block-head">
                        <h2>{preview.filename}</h2>
                        <span className="small muted">{SOURCE_TEXT[preview.source]}</span>
                    </div>
                    {preview.already_imported_at && (
                        <p role="status" className="alert">
                            This exact file was already imported on{" "}
                            {new Date(preview.already_imported_at).toLocaleDateString("en-GB")}.
                        </p>
                    )}
                    <div className="panel">
                        <label className="field" style={{ maxWidth: "22rem" }}>
                            <span>Read as</span>
                            <select className="select" value={importer} onChange={(e) => handleImporter(e.target.value)}>
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
                    </div>
                    {preview.error && (
                        <p role="alert" className="alert">
                            {preview.error}
                        </p>
                    )}

                    <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
                        <p className="lead">
                            {preview.new_count} new
                            {preview.duplicate_count > 0 && (
                                <span className="muted"> · {preview.duplicate_count} already imported, skipped</span>
                            )}
                            {preview.period && <span className="muted"> · counts toward {monthName(preview.period)}</span>}
                        </p>
                        <div className="edit-actions">
                            <button className="btn" onClick={reset} disabled={busy}>
                                Cancel
                            </button>
                            <button
                                className="btn btn-primary"
                                onClick={handleConfirm}
                                disabled={busy || !!preview.error || preview.new_count === 0 || !currentConfig()}
                            >
                                Import {preview.new_count} transactions
                            </button>
                        </div>
                    </div>

                    {preview.transactions.length > 0 && (
                        <div className="table-wrap">
                            <table className="table">
                                <thead>
                                    <tr>
                                        <th>Date</th>
                                        <th>Description</th>
                                        <th>Category</th>
                                        <th className="num">Amount</th>
                                        <th />
                                    </tr>
                                </thead>
                                <tbody>
                                    {preview.transactions.slice(0, PREVIEW_ROWS).map((t, i) => (
                                        <tr key={i} className={t.duplicate ? "dim" : undefined}>
                                            <td className="cell-date">{dayName(t.booked_on)}</td>
                                            <td className="cell-desc">{t.description}</td>
                                            <td>{t.category}</td>
                                            <td className="num">{kr(t.amount_minor)}</td>
                                            <td className="num">
                                                {t.duplicate ? (
                                                    <span className="small">Already imported</span>
                                                ) : (
                                                    <span className="tag tag-personal">New</span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                    {preview.transactions.length > PREVIEW_ROWS && (
                        <p className="muted">…and {preview.transactions.length - PREVIEW_ROWS} more</p>
                    )}
                </section>
            )}

            {history.length > 0 && (
                <section className="block">
                    <div className="block-head">
                        <h2>Imported into {account?.name}</h2>
                    </div>
                    <ul className="list">
                        {history.map((imp) => (
                            <li key={imp.id} className="list-row">
                                <span className="desc">{imp.filename}</span>
                                <button className="link small" onClick={() => handleUndo(imp)}>
                                    Undo
                                </button>
                                <span className="sub">
                                    {imp.period_start && imp.period_end
                                        ? `${dayName(imp.period_start)} – ${dayName(imp.period_end)} · `
                                        : ""}
                                    {imp.transaction_count} transactions
                                    {imp.duplicate_count > 0 && `, ${imp.duplicate_count} skipped`}
                                    {imp.period && (
                                        <>
                                            {" · counts toward "}
                                            <label className="link period-pick">
                                                {monthName(imp.period)}
                                                <input
                                                    type="month"
                                                    value={imp.period}
                                                    onChange={(e) => e.target.value && handlePeriod(imp, e.target.value)}
                                                    aria-label={`Month ${imp.filename} counts toward`}
                                                />
                                            </label>
                                        </>
                                    )}
                                </span>
                            </li>
                        ))}
                    </ul>
                </section>
            )}
        </div>
    );
};

export default ImportWizard;
