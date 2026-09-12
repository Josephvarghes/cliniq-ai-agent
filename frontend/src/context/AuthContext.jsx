import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem('cliniq_token') || null);
  const [role, setRole] = useState(localStorage.getItem('cliniq_role') || null);
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('cliniq_user')) || null;
    } catch {
      return null;
    }
  });

  const login = (newToken, newRole, newUser) => {
    setToken(newToken);
    setRole(newRole);
    setUser(newUser);
    localStorage.setItem('cliniq_token', newToken);
    localStorage.setItem('cliniq_role', newRole);
    localStorage.setItem('cliniq_user', JSON.stringify(newUser));
  };

  const logout = () => {
    setToken(null);
    setRole(null);
    setUser(null);
    localStorage.removeItem('cliniq_token');
    localStorage.removeItem('cliniq_role');
    localStorage.removeItem('cliniq_user');
  };

  return (
    <AuthContext.Provider value={{ token, role, user, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
