import React, { useState } from "react";
import { createUser } from "../api";

const UserCreator = ({ fetchUsers }) => {
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  const handleCreateUser = async () => {
    if (!name.trim()) return;
    setCreating(true);
    try {
      await createUser(name);
      setName("");
      fetchUsers();
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="p-4 border rounded-md bg-white shadow-sm">
      <h2 className="text-xl font-semibold mb-4">Create User</h2>
      
      <input 
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Enter user name"
        className="px-3 py-2 border rounded w-full mb-2"
      />
      
      <button 
        onClick={handleCreateUser}
        disabled={creating}
        className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:bg-green-300 transition-colors w-full"
      >
        {creating ? "Creating..." : "Create User"}
      </button>
    </div>
  );
};

export default UserCreator;