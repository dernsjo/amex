import React, { useState } from "react";
import { createUser } from "../api";

function UserForm({ fetchUsers }) {
    const [name, setName] = useState("");

    const handleCreateUser = async (event) => {
        event.preventDefault();
        await createUser(name);
        setName("");
        fetchUsers();
    };

    return (
        <div>
            <h2>Create User</h2>
            <form onSubmit={handleCreateUser}>
                <input
                    type="text"
                    placeholder="Enter user name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                />
                <button type="submit">Create User</button>
            </form>
        </div>
    );
}

export default UserForm;
