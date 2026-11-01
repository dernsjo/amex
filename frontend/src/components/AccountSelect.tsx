import type { Account } from "../api";

interface Props {
    accounts: Account[];
    value: number | null;
    onChange: (accountId: number) => void;
}

const AccountSelect = ({ accounts, value, onChange }: Props) => (
    <select value={value ?? ""} onChange={(e) => onChange(Number(e.target.value))} required>
        <option value="" disabled>
            Account…
        </option>
        {accounts.map((a) => (
            <option key={a.id} value={a.id}>
                {a.name}
            </option>
        ))}
    </select>
);

export default AccountSelect;
