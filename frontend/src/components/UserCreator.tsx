import { useState } from "react";
import { createUser, errorMessage } from "../api";

interface Props {
    fetchUsers: () => Promise<void>;
}

const UserCreator = ({ fetchUsers }: Props) => {
    const [name, setName] = useState("");
    const [creating, setCreating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleCreateUser = async () => {
        if (!name.trim()) return;
        setCreating(true);
        setError(null);
        try {
            await createUser(name.trim());
            setName("");
            await fetchUsers();
        } catch (e) {
            setError(errorMessage(e));
        } finally {
            setCreating(false);
        }
    };

    return (
        <div>
            <h2>Create User</h2>
            <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter user name"
            />
            <button onClick={handleCreateUser} disabled={creating}>
                {creating ? "Creating..." : "Create User"}
            </button>
            {error && <p role="alert">{error}</p>}
        </div>
    );
};

export default UserCreator;
