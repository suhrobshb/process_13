/**
 * Authentication Context
 * ======================
 * 
 * Global authentication state management with JWT tokens
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiClient } from '@/lib/api';

// =============================================================================
// Types and Interfaces
// =============================================================================

export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  role: UserRole;
  permissions: Permission[];
  preferences: UserPreferences;
  createdAt: string;
  lastLogin: string;
  isActive: boolean;
}

export interface UserRole {
  id: string;
  name: string;
  description: string;
  level: number; // 0 = User, 1 = Editor, 2 = Admin, 3 = Super Admin
  permissions: Permission[];
}

export interface Permission {
  id: string;
  name: string;
  description: string;
  resource: string;
  action: string;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  timezone: string;
  notifications: {
    email: boolean;
    push: boolean;
    workflow: boolean;
    system: boolean;
  };
  dashboard: {
    layout: 'grid' | 'list';
    widgets: string[];
    refreshInterval: number;
  };
}

export interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  permissions: Permission[];
}

export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface RegisterData {
  email: string;
  password: string;
  name: string;
  confirmPassword: string;
}

export interface AuthContextType {
  // State
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  permissions: Permission[];
  
  // Actions
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  refreshAuth: () => Promise<void>;
  updateProfile: (updates: Partial<User>) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  
  // Permission helpers
  hasPermission: (permission: string) => boolean;
  hasRole: (role: string) => boolean;
  canAccess: (resource: string, action: string) => boolean;
}

// =============================================================================
// Default Values
// =============================================================================

const defaultAuthState: AuthState = {
  user: null,
  token: null,
  refreshToken: null,
  isLoading: true,
  isAuthenticated: false,
  permissions: [],
};

const defaultUserPreferences: UserPreferences = {
  theme: 'system',
  language: 'en',
  timezone: 'UTC',
  notifications: {
    email: true,
    push: true,
    workflow: true,
    system: false,
  },
  dashboard: {
    layout: 'grid',
    widgets: ['stats', 'recent-workflows', 'metrics'],
    refreshInterval: 30000,
  },
};

// =============================================================================
// Context Creation
// =============================================================================

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// =============================================================================
// Auth Provider Component
// =============================================================================

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>(defaultAuthState);

  // Initialize auth state from localStorage
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const token = localStorage.getItem('auth_token');
        const refreshToken = localStorage.getItem('refresh_token');
        
        if (token && refreshToken) {
          // Validate token and get user info
          const user = await apiClient.validateToken(token);
          setAuthState({
            user,
            token,
            refreshToken,
            isLoading: false,
            isAuthenticated: true,
            permissions: user.permissions,
          });
        } else {
          setAuthState(prev => ({ ...prev, isLoading: false }));
        }
      } catch (error) {
        // Token is invalid, clear storage
        localStorage.removeItem('auth_token');
        localStorage.removeItem('refresh_token');
        setAuthState(prev => ({ ...prev, isLoading: false }));
      }
    };

    initializeAuth();
  }, []);

  // Auto-refresh token before expiration
  useEffect(() => {
    if (!authState.token) return;

    const refreshInterval = setInterval(async () => {
      try {
        await refreshAuth();
      } catch (error) {
        console.error('Token refresh failed:', error);
        logout();
      }
    }, 15 * 60 * 1000); // Refresh every 15 minutes

    return () => clearInterval(refreshInterval);
  }, [authState.token]);

  // =============================================================================
  // Authentication Actions
  // =============================================================================

  const login = async (credentials: LoginCredentials): Promise<void> => {
    try {
      setAuthState(prev => ({ ...prev, isLoading: true }));
      
      const response = await apiClient.login(credentials);
      const { user, token, refreshToken } = response;
      
      // Store tokens
      localStorage.setItem('auth_token', token);
      localStorage.setItem('refresh_token', refreshToken);
      
      if (credentials.rememberMe) {
        localStorage.setItem('remember_me', 'true');
      }
      
      setAuthState({
        user,
        token,
        refreshToken,
        isLoading: false,
        isAuthenticated: true,
        permissions: user.permissions,
      });
    } catch (error) {
      setAuthState(prev => ({ ...prev, isLoading: false }));
      throw error;
    }
  };

  const register = async (data: RegisterData): Promise<void> => {
    try {
      setAuthState(prev => ({ ...prev, isLoading: true }));
      
      const response = await apiClient.register(data);
      const { user, token, refreshToken } = response;
      
      // Store tokens
      localStorage.setItem('auth_token', token);
      localStorage.setItem('refresh_token', refreshToken);
      
      setAuthState({
        user,
        token,
        refreshToken,
        isLoading: false,
        isAuthenticated: true,
        permissions: user.permissions,
      });
    } catch (error) {
      setAuthState(prev => ({ ...prev, isLoading: false }));
      throw error;
    }
  };

  const logout = (): void => {
    // Clear tokens
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('remember_me');
    
    // Clear API client token
    apiClient.setAuthToken(null);
    
    setAuthState(defaultAuthState);
  };

  const refreshAuth = async (): Promise<void> => {
    try {
      const refreshToken = authState.refreshToken || localStorage.getItem('refresh_token');
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }
      
      const response = await apiClient.refreshToken(refreshToken);
      const { user, token, refreshToken: newRefreshToken } = response;
      
      // Update stored tokens
      localStorage.setItem('auth_token', token);
      localStorage.setItem('refresh_token', newRefreshToken);
      
      setAuthState(prev => ({
        ...prev,
        user,
        token,
        refreshToken: newRefreshToken,
        permissions: user.permissions,
      }));
    } catch (error) {
      logout();
      throw error;
    }
  };

  const updateProfile = async (updates: Partial<User>): Promise<void> => {
    try {
      const updatedUser = await apiClient.updateProfile(updates);
      setAuthState(prev => ({
        ...prev,
        user: updatedUser,
        permissions: updatedUser.permissions,
      }));
    } catch (error) {
      throw error;
    }
  };

  const changePassword = async (currentPassword: string, newPassword: string): Promise<void> => {
    try {
      await apiClient.changePassword(currentPassword, newPassword);
    } catch (error) {
      throw error;
    }
  };

  // =============================================================================
  // Permission Helpers
  // =============================================================================

  const hasPermission = (permission: string): boolean => {
    return authState.permissions.some(p => p.name === permission);
  };

  const hasRole = (role: string): boolean => {
    return authState.user?.role.name === role;
  };

  const canAccess = (resource: string, action: string): boolean => {
    return authState.permissions.some(p => p.resource === resource && p.action === action);
  };

  // =============================================================================
  // Context Value
  // =============================================================================

  const contextValue: AuthContextType = {
    // State
    user: authState.user,
    token: authState.token,
    isLoading: authState.isLoading,
    isAuthenticated: authState.isAuthenticated,
    permissions: authState.permissions,
    
    // Actions
    login,
    register,
    logout,
    refreshAuth,
    updateProfile,
    changePassword,
    
    // Permission helpers
    hasPermission,
    hasRole,
    canAccess,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

// =============================================================================
// Custom Hook
// =============================================================================

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// =============================================================================
// Higher-Order Component for Route Protection
// =============================================================================

export const withAuth = <P extends object>(
  Component: React.ComponentType<P>,
  requiredPermissions?: string[]
) => {
  const AuthenticatedComponent: React.FC<P> = (props) => {
    const { isAuthenticated, hasPermission, isLoading } = useAuth();

    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      );
    }

    if (!isAuthenticated) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Authentication Required</h2>
            <p className="text-gray-600 mb-6">Please log in to access this page.</p>
            <button
              onClick={() => window.location.href = '/login'}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Go to Login
            </button>
          </div>
        </div>
      );
    }

    if (requiredPermissions && !requiredPermissions.every(hasPermission)) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Access Denied</h2>
            <p className="text-gray-600 mb-6">You don't have permission to access this resource.</p>
            <button
              onClick={() => window.history.back()}
              className="bg-gray-600 text-white px-6 py-2 rounded-lg hover:bg-gray-700 transition-colors"
            >
              Go Back
            </button>
          </div>
        </div>
      );
    }

    return <Component {...props} />;
  };

  AuthenticatedComponent.displayName = `withAuth(${Component.displayName || Component.name})`;
  return AuthenticatedComponent;
};

export default AuthProvider;