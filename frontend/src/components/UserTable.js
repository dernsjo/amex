import React, { useEffect, useState } from "react";
import { deleteUser, getUsers } from "../api";

function UserTable() {
    const [users, setUsers] = useState([]);
    const [showTable, setShowTable] = useState(false);

    useEffect(() => {
        if (showTable) {
            loadUsers();
        }
    }, [showTable]);

    const loadUsers = async () => {
        const data = await getUsers();
        setUsers(data);
    };

    const handleDeleteUser = async (userId) => {
        await deleteUser(userId);
        loadUsers();
    };

    return (
        <div>
            <h2>User List</h2>
            <button onClick={() => setShowTable(!showTable)}>
                {showTable ? "Hide Users" : "Show Users"}
            </button>
            {showTable && (
                <table border="1">
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