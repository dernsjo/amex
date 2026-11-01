import type { CsvMapping, ImportPreview } from "../api";

// strptime formats the backend understands, with what they look like.
const DATE_FORMATS: [string, string][] = [
    ["%Y-%m-%d", "2025-07-31"],
    ["%Y%m%d", "20250731"],
    ["%Y/%m/%d", "2025/07/31"],
    ["%d.%m.%Y", "31.07.2025"],
    ["%d/%m/%Y", "31/07/2025"],
    ["%m/%d/%Y", "07/31/2025"],
    ["%d-%m-%Y", "31-07-2025"],
];

type Draft = Omit<CsvMapping, "date_column" | "description_column" | "amount_column"> & {
    date_column: string;
    description_column: string;
    amount_column: string;
};

interface Props {
    preview: ImportPreview;
    mapping: Draft;
    onChange: (mapping: Draft) => void;
}

/** Which columns mean what, with the file's first rows underneath to choose from. */
const MappingForm = ({ preview, mapping, onChange }: Props) => {
    const columnSelect = (label: string, key: "date_column" | "description_column" | "amount_column") => (
        <label className="field grow">
            <span>{label}</span>
            <select className="select" value={mapping[key]} onChange={(e) => onChange({ ...mapping, [key]: e.target.value })}>
                <option value="">Choose a column…</option>
                {preview.columns.map((c) => (
                    <option key={c} value={c}>
                        {c}
                    </option>
                ))}
            </select>
        </label>
    );

    return (
        <div style={{ display: "grid", gap: "1rem" }}>
            <div className="row">
                {columnSelect("Date column", "date_column")}
                {columnSelect("Description column", "description_column")}
                {columnSelect("Amount column", "amount_column")}
            </div>
            <div className="row">
                <label className="field grow">
                    <span>Dates look like</span>
                    <select
                        className="select"
                        value={mapping.date_format ?? ""}
                        onChange={(e) => onChange({ ...mapping, date_format: e.target.value || null })}
                    >
                        <option value="">Work it out</option>
                        {DATE_FORMATS.map(([format, example]) => (
                            <option key={format} value={format}>
                                {example}
                            </option>
                        ))}
                    </select>
                </label>
                <label className="field grow">
                    <span>Amounts look like</span>
                    <select
                        className="select"
                        value={mapping.decimal_separator}
                        onChange={(e) => onChange({ ...mapping, decimal_separator: e.target.value as "," | "." })}
                    >
                        <option value=",">1 234,56</option>
                        <option value=".">1,234.56</option>
                    </select>
                </label>
                <label className="field grow">
                    <span>Money spent is</span>
                    <select
                        className="select"
                        value={mapping.spending_is_negative ? "negative" : "positive"}
                        onChange={(e) => onChange({ ...mapping, spending_is_negative: e.target.value === "negative" })}
                    >
                        <option value="negative">Negative (−250,00)</option>
                        <option value="positive">Positive (250,00)</option>
                    </select>
                </label>
            </div>
            <div className="sample-wrap">
                <table className="table sample">
                    <thead>
                        <tr>
                            {preview.columns.map((c) => (
                                <th key={c}>{c}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {preview.sample_rows.map((row, i) => (
                            <tr key={i}>
                                {row.map((cell, j) => (
                                    <td key={j}>{cell}</td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export type { Draft as MappingDraft };
export default MappingForm;
