import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { addMonths, kr, monthName, monthShort } from "../api";
import type { Trends } from "../api";

/** The Leva mark: one block cut into two shares (60/40) by the motif's gap. */
export const Mark = ({ size = 28 }: { size?: number }) => (
    <svg viewBox="0 0 32 32" width={size} height={size} aria-hidden="true">
        <rect x="0" y="0" width="18" height="32" fill="var(--accent, #d0106f)" />
        <rect x="21" y="0" width="11" height="32" fill="var(--ink, #000)" />
    </svg>
);

export const Wordmark = () => (
    <span className="wordmark">
        <Mark />
        leva
    </span>
);

export interface Share {
    value: number;
    className?: string;
    color?: string;
    label?: ReactNode;
    title?: string;
}

/** The motif at data scale: parts of a whole, side by side, cut by a 4px gap. Zero parts are left out. */
export const ShareBar = ({ parts, className = "", style }: { parts: Share[]; className?: string; style?: CSSProperties }) => (
    <div className={`share ${className}`} style={style} role="presentation">
        {parts
            .filter((p) => p.value > 0)
            .map((p, i) => (
                <span
                    key={i}
                    className={p.className}
                    title={p.title}
                    style={{ flexGrow: p.value, flexBasis: 0, background: p.color, ["--i" as string]: i }}
                >
                    {p.label}
                </span>
            ))}
    </div>
);

/** Members keep one colour each, by their position in the household (validated order). */
export const memberColor = (index: number) => `var(--member-${(index % 4) + 1})`;

export function Segmented<T extends string>({
    value,
    options,
    onChange,
    label,
}: {
    value: T;
    options: { value: T; label: string }[];
    onChange: (value: T) => void;
    label: string;
}) {
    return (
        <div className="segmented" role="group" aria-label={label}>
            {options.map((o) => (
                <button key={o.value} type="button" aria-pressed={o.value === value} onClick={() => onChange(o.value)}>
                    {o.label}
                </button>
            ))}
        </div>
    );
}

/** ‹ November 2026 › — the label opens the native month picker. */
export const MonthStepper = ({ month, onChange }: { month: string; onChange: (month: string) => void }) => (
    <div className="month">
        <button type="button" onClick={() => onChange(addMonths(month, -1))} aria-label="Previous month">
            ‹
        </button>
        <label className="month-label">
            {monthName(month)}
            <input
                type="month"
                value={month}
                onChange={(e) => e.target.value && onChange(e.target.value)}
                aria-label="Choose month"
            />
        </label>
        <button type="button" onClick={() => onChange(addMonths(month, 1))} aria-label="Next month">
            ›
        </button>
    </div>
);

export const TREND_MONTHS = 12;

/** Twelve months of spending as bars; the chosen month in the accent. Choosing a bar moves the whole view. */
export const TrendBars = ({ trends, month, onSelect }: { trends: Trends; month: string; onSelect: (m: string) => void }) => {
    const max = Math.max(1, ...trends.months.map((p) => p.spent_minor));
    return (
        <div className="trend">
            <div className="trend-bars" role="group" aria-label="Spending per month">
                {trends.months.map((p, i) => {
                    const h = `${(Math.max(0, p.spent_minor) / max) * 100}%`;
                    return (
                        <button
                            key={p.month}
                            type="button"
                            className={`trend-bar${i < 2 ? " edge-start" : i >= trends.months.length - 2 ? " edge-end" : ""}`}
                            aria-pressed={p.month === month}
                            aria-label={`${monthName(p.month)}: ${kr(p.spent_minor)}`}
                            onClick={() => onSelect(p.month)}
                            style={{ ["--i" as string]: i, ["--h" as string]: `calc((14rem - 1.65rem) * ${Math.max(0, p.spent_minor) / max})` }}
                        >
                            <span className="tip">
                                {monthShort(p.month)} {kr(p.spent_minor)}
                            </span>
                            <span className="bar" style={{ height: `calc(${h} - 1.65rem)` }} />
                            <span className="m">{monthShort(p.month).slice(0, 1)}</span>
                        </button>
                    );
                })}
            </div>
        </div>
    );
};

// ---------- dialogs: confirm and prompt, in place of window.confirm/prompt ----------

interface DialogRequest {
    title: string;
    body?: ReactNode;
    action: string;
    input?: { label: string; value: string };
    resolve: (value: string | null) => void;
}

interface Dialogs {
    confirm: (title: string, body: ReactNode, action: string) => Promise<boolean>;
    prompt: (title: string, label: string, value: string, action?: string) => Promise<string | null>;
}

const DialogContext = createContext<Dialogs | null>(null);

export const useDialogs = () => {
    const dialogs = useContext(DialogContext);
    if (!dialogs) throw new Error("useDialogs outside DialogProvider");
    return dialogs;
};

export const DialogProvider = ({ children }: { children: ReactNode }) => {
    const [request, setRequest] = useState<DialogRequest | null>(null);
    const [value, setValue] = useState("");
    const ref = useRef<HTMLDialogElement>(null);

    useEffect(() => {
        const dialog = ref.current;
        if (request && dialog && !dialog.open) dialog.showModal();
    }, [request]);

    const finish = (result: string | null) => {
        ref.current?.close();
        request?.resolve(result);
        setRequest(null);
    };

    const confirm = useCallback(
        (title: string, body: ReactNode, action: string) =>
            new Promise<boolean>((resolve) => setRequest({ title, body, action, resolve: (v) => resolve(v !== null) })),
        [],
    );
    const prompt = useCallback(
        (title: string, label: string, initial: string, action = "Save") =>
            new Promise<string | null>((resolve) => {
                setValue(initial);
                setRequest({ title, action, input: { label, value: initial }, resolve });
            }),
        [],
    );

    return (
        <DialogContext.Provider value={{ confirm, prompt }}>
            {children}
            <dialog ref={ref} className="dialog" onCancel={() => finish(null)} aria-labelledby="dialog-title">
                {request && (
                    <form
                        method="dialog"
                        onSubmit={(e) => {
                            e.preventDefault();
                            finish(request.input ? value : "ok");
                        }}
                    >
                        <h2 id="dialog-title">{request.title}</h2>
                        {request.body && <p>{request.body}</p>}
                        {request.input && (
                            <label className="field" style={{ marginTop: "1rem" }}>
                                <span>{request.input.label}</span>
                                <input
                                    className="input"
                                    value={value}
                                    onChange={(e) => setValue(e.target.value)}
                                    autoFocus
                                    required
                                />
                            </label>
                        )}
                        <div className="edit-actions">
                            <button type="button" className="btn" onClick={() => finish(null)}>
                                Cancel
                            </button>
                            <button type="submit" className="btn btn-ink" autoFocus={!request.input}>
                                {request.action}
                            </button>
                        </div>
                    </form>
                )}
            </dialog>
        </DialogContext.Provider>
    );
};
