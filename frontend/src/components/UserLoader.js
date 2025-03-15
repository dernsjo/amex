import React, { useState } from "react";

const UserLoader = ({ users, fetchUsers }) => {
  const [loading, setLoading] = useState(false);

  const handleLoadUsers = async () => {
    setLoading(true);
    try {
      await fetchUsers();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 border rounded-md bg-white shadow-sm">
      <h2 className="text-xl font-semibold mb-4">Users</h2>
      
      <button 
        onClick={handleLoadUsers}
        disabled={loading}
        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-blue-300 transition-colors"
      >
        {loading ? "Loading..." : "Load Users"}
      </button>
      
      {users.length > 0 ? (
        <ul className="mt-4 space-y-2">
          {users.map((user) => (
            <li 
              key={user.id}
              className="p-2 bg-gray-100 rounded flex justify-between items-center"
            >
              <span>{user.name}</span>
              {user.email && <span className="text-gray-500 text-sm">{user.email}</span>}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-gray-500">No users loaded. Click the button above to load users.</p>
      )}
    </div>
  );
};

export default UserLoader;