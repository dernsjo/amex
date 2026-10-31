import { useState } from "react";
import { deleteUser, errorMessage } from "../api";
import type { User } from "../api";

interface Props {
    users: User[];
    fetchUsers: () => Promise<void>;
}

function UserTable({ users, fetchUsers }: Props) {
    const [showTable, setShowTable] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleDeleteUser = async (userId: number) => {
        setError(null);
        try {
            await deleteUser(userId);
            await fetchUsers();
        } catch (e) {
            setError(errorMessage(e));
        }
    };

    return (
        <div>
            <h2>User List</h2>
            <button onClick={() => setShowTable(!showTable)}>
                {showTable ? "Hide Users" : "Show Users"}
            </button>
            {error && <p role="alert">{error}</p>}
            {showTable && (
                <table border={1}>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users.map((user) => (
                            <tr key={user.id}>
                                <td>{user.id}</td>
                                <td>{user.name}</td>
                                <td>
                                    <button onClick={() => handleDeleteUser(user.id)}>Delete</button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
}

export default UserTable;
