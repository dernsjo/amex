import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
    createCategory,
    createRule,
    deleteCategory,
    deleteRule,
    errorMessage,
    getCategories,
    getRules,
    renameCategory,
} from "../api";
import type { Category, CategoryRule } from "../api";
import { useDialogs } from "./ui";

interface Props {
    householdId: number | null; // null: the categories of your own, unshared accounts
    scopeName: string;
    onChanged: () => Promise<void>; // categories or transactions may have changed
}

/** A scope's categories and the rules that sort transactions into them. */
const CategoryPanel = ({ householdId, scopeName, onChanged }: Props) => {
    const dialogs = useDialogs();
    const [categories, setCategories] = useState<Category[]>([]);
    const [rules, setRules] = useState<CategoryRule[]>([]);
    const [newCategory, setNewCategory] = useState("");
    const [pattern, setPattern] = useState("");
    const [ruleCategory, setRuleCategory] = useState("");
    const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null);

    const fetchScope = useCallback(async () => {
        const [c, r] = await Promise.all([getCategories(householdId), getRules(householdId)]);
        setCategories(c);
        setRules(r);
    }, [householdId]);

    useEffect(() => {
        fetchScope().catch((e) => setMessage({ text: errorMessage(e), error: true }));
    }, [fetchScope]);

    const run = async (action: () => Promise<string | void>) => {
        setMessage(null);
        try {
            const done = await action();
            await Promise.all([fetchScope(), onChanged()]);
            if (done) setMessage({ text: done, error: false });
        } catch (e) {
            setMessage({ text: errorMessage(e), error: true });
        }
    };

    const handleAdd = (e: FormEvent) => {
        e.preventDefault();
        run(async () => {
            await createCategory(householdId, newCategory.trim());
            setNewCategory("");
        });
    };

    const handleRename = async (c: Category) => {
        const name = (await dialogs.prompt(`Rename ${c.name}`, "New name", c.name))?.trim();
        if (name && name !== c.name)
            run(async () => {
                await renameCategory(householdId, c.id, name);
            });
    };

    const handleDelete = async (c: Category) => {
        const ok = await dialogs.confirm(
            `Delete ${c.name}?`,
            "Its rules and budget go too, and its transactions are sorted again.",
            "Delete category",
        );
        if (ok) run(() => deleteCategory(householdId, c.id));
    };

    const handleAddRule = (e: FormEvent) => {
        e.preventDefault();
        const category = ruleCategory || categories[0]?.name;
        run(async () => {
            const result = await createRule(householdId, pattern.trim(), category);
            setPattern("");
            return `Rule added; ${result.recategorized} transaction(s) moved to ${category}.`;
        });
    };

    return (
        <div className="cols">
            {message && (
                <p role={message.error ? "alert" : "status"} className={message.error ? "alert" : "status"} style={{ gridColumn: "1 / -1" }}>
                    {message.text}
                </p>
            )}
            <section className="block span-5">
                <div className="block-head">
                    <h2>Categories</h2>
                    <span className="small muted">For {scopeName}</span>
                </div>
                <ul className="chips">
                    {categories.map((c) => (
                        <li key={c.id} className="chip">
                            {c.name}
                            <button onClick={() => handleRename(c)} aria-label={`Rename ${c.name}`}>
                                Rename
                            </button>
                            {!c.is_fallback && (
                                <button onClick={() => handleDelete(c)} aria-label={`Delete ${c.name}`}>
                                    Delete
                                </button>
                            )}
                        </li>
                    ))}
                </ul>
                <form onSubmit={handleAdd} className="row">
                    <label className="field grow">
                        <span>New category</span>
                        <input className="input" value={newCategory} onChange={(e) => setNewCategory(e.target.value)} required />
                    </label>
                    <button type="submit" className="btn btn-ink">
                        Add
                    </button>
                </form>
            </section>

            <section className="block span-7">
                <div className="block-head">
                    <h2>Rules</h2>
                    <span className="small muted">The longest matching text wins</span>
                </div>
                <p>
                    A description containing the text goes to the category. Your rules come before the built-in keywords,
                    and categories you pick by hand are never changed.
                </p>
                {rules.length > 0 && (
                    <ul className="list">
                        {rules.map((r) => (
                            <li key={r.id} className="rule">
                                <span className="pattern">{r.pattern}</span>
                                <span className="arrow" aria-hidden="true">
                                    →
                                </span>
                                <span>
                                    <span className="sr-only">goes to </span>
                                    {r.category}
                                </span>
                                <button className="btn btn-small" onClick={() => run(() => deleteRule(householdId, r.id))}>
                                    Delete
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
                <form onSubmit={handleAddRule} className="panel">
                    <div className="row">
                        <label className="field grow">
                            <span>When the description contains</span>
                            <input
                                className="input"
                                placeholder="e.g. ICA MAXI"
                                value={pattern}
                                onChange={(e) => setPattern(e.target.value)}
                                minLength={2}
                                required
                            />
                        </label>
                        <label className="field grow">
                            <span>Put it in</span>
                            <select className="select" value={ruleCategory} onChange={(e) => setRuleCategory(e.target.value)}>
                                {categories.map((c) => (
                                    <option key={c.id} value={c.name}>
                                        {c.name}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <button type="submit" className="btn btn-ink">
                            Add rule
                        </button>
                    </div>
                </form>
            </section>
        </div>
    );
};

export default CategoryPanel;
