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

interface Props {
    householdId: number | null; // null: the categories of your own, unshared accounts
    scopeName: string;
    onChanged: () => Promise<void>; // categories or transactions may have changed
}

/** A scope's categories and the rules that sort transactions into them. */
const CategoryPanel = ({ householdId, scopeName, onChanged }: Props) => {
    const [categories, setCategories] = useState<Category[]>([]);
    const [rules, setRules] = useState<CategoryRule[]>([]);
    const [newCategory, setNewCategory] = useState("");
    const [pattern, setPattern] = useState("");
    const [ruleCategory, setRuleCategory] = useState("");
    const [message, setMessage] = useState<string | null>(null);

    const fetchScope = useCallback(async () => {
        const [c, r] = await Promise.all([getCategories(householdId), getRules(householdId)]);
        setCategories(c);
        setRules(r);
    }, [householdId]);

    useEffect(() => {
        fetchScope().catch((e) => setMessage(errorMessage(e)));
    }, [fetchScope]);

    const run = async (action: () => Promise<string | void>) => {
        setMessage(null);
        try {
            const done = await action();
            await Promise.all([fetchScope(), onChanged()]);
            if (done) setMessage(done);
        } catch (e) {
            setMessage(errorMessage(e));
        }
    };

    const handleAdd = (e: FormEvent) => {
        e.preventDefault();
        run(async () => {
            await createCategory(householdId, newCategory.trim());
            setNewCategory("");
        });
    };

    const handleRename = (c: Category) => {
        const name = window.prompt(`Rename ${c.name} to`, c.name)?.trim();
        if (name && name !== c.name)
            run(async () => {
                await renameCategory(householdId, c.id, name);
            });
    };

    const handleDelete = (c: Category) => {
        if (!window.confirm(`Delete ${c.name}? Its rules and budget go too, and its transactions are sorted again.`))
            return;
        run(() => deleteCategory(householdId, c.id));
    };

    const handleAddRule = (e: FormEvent) => {
        e.preventDefault();
        const category = ruleCategory || categories[0]?.name;
        run(async () => {
            const result = await createRule(householdId, pattern.trim(), category);
            setPattern("");
            return `Rule added; ${result.recategorized} transaction(s) moved.`;
        });
    };

    return (
        <details>
            <summary>Categories for {scopeName}</summary>
            {message && <p role="status">{message}</p>}
            <ul style={{ listStyle: "none", padding: 0 }}>
                {categories.map((c) => (
                    <li key={c.id}>
                        {c.name} <button onClick={() => handleRename(c)}>Rename</button>
                        {!c.is_fallback && <button onClick={() => handleDelete(c)}>Delete</button>}
                    </li>
                ))}
            </ul>
            <form onSubmit={handleAdd}>
                <input
                    placeholder="New category"
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    required
                />
                <button type="submit">Add category</button>
            </form>

            <h4>Rules</h4>
            <p>
                A description containing the text goes to the category. These come before the built-in keywords, and
                the longest matching text wins. Categories you pick by hand are never changed.
            </p>
            {rules.length > 0 && (
                <ul style={{ listStyle: "none", padding: 0 }}>
                    {rules.map((r) => (
                        <li key={r.id}>
                            "{r.pattern}" → {r.category}{" "}
                            <button onClick={() => run(() => deleteRule(householdId, r.id))}>Delete</button>
                        </li>
                    ))}
                </ul>
            )}
            <form onSubmit={handleAddRule}>
                <input
                    placeholder="Text, e.g. ICA MAXI"
                    value={pattern}
                    onChange={(e) => setPattern(e.target.value)}
                    minLength={2}
                    required
                />
                →{" "}
                <select value={ruleCategory} onChange={(e) => setRuleCategory(e.target.value)}>
                    {categories.map((c) => (
                        <option key={c.id} value={c.name}>
                            {c.name}
                        </option>
                    ))}
                </select>
                <button type="submit">Add rule</button>
            </form>
        </details>
    );
};

export default CategoryPanel;
