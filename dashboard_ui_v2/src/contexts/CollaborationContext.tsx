/**
 * Collaboration Context
 * =====================
 * 
 * Real-time collaboration state management with WebSocket integration
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Node, Edge } from 'reactflow';
import { useAuth } from './AuthContext';
import { toast } from '@/components/ui/use-toast';

// =============================================================================
// Types and Interfaces
// =============================================================================

export interface CollaborationUser {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  cursor?: {
    x: number;
    y: number;
  };
  lastActivity: string;
  color: string;
  isActive: boolean;
}

export interface CollaborationSession {
  id: string;
  workflowId: string;
  participants: CollaborationUser[];
  createdAt: string;
  isActive: boolean;
}

export interface CollaborationEvent {
  id: string;
  type: 'join' | 'leave' | 'node_update' | 'edge_update' | 'cursor_move' | 'selection_change' | 'comment' | 'lock' | 'unlock';
  userId: string;
  workflowId: string;
  timestamp: string;
  data: any;
}

export interface Comment {
  id: string;
  workflowId: string;
  nodeId?: string;
  authorId: string;
  author: CollaborationUser;
  content: string;
  position?: { x: number; y: number };
  createdAt: string;
  updatedAt: string;
  resolved: boolean;
  replies: Comment[];
  mentions: string[];
}

export interface NodeLock {
  nodeId: string;
  userId: string;
  userName: string;
  lockedAt: string;
  expiresAt: string;
}

export interface CollaborationState {
  session: CollaborationSession | null;
  activeUsers: CollaborationUser[];
  comments: Comment[];
  locks: NodeLock[];
  isConnected: boolean;
  isJoining: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'reconnecting';
}

export interface CollaborationContextType {
  // State
  session: CollaborationSession | null;
  activeUsers: CollaborationUser[];
  comments: Comment[];
  locks: NodeLock[];
  isConnected: boolean;
  isJoining: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'reconnecting';
  
  // Actions
  joinSession: (workflowId: string) => Promise<void>;
  leaveSession: () => void;
  sendCursorPosition: (x: number, y: number) => void;
  sendNodeUpdate: (nodeId: string, nodeData: any) => void;
  sendEdgeUpdate: (edgeId: string, edgeData: any) => void;
  sendSelectionChange: (selectedNodes: string[], selectedEdges: string[]) => void;
  
  // Comments
  addComment: (content: string, nodeId?: string, position?: { x: number; y: number }) => Promise<Comment>;
  updateComment: (commentId: string, content: string) => Promise<void>;
  deleteComment: (commentId: string) => Promise<void>;
  resolveComment: (commentId: string) => Promise<void>;
  replyToComment: (commentId: string, content: string) => Promise<Comment>;
  
  // Locking
  lockNode: (nodeId: string) => Promise<void>;
  unlockNode: (nodeId: string) => Promise<void>;
  isNodeLocked: (nodeId: string) => boolean;
  getNodeLock: (nodeId: string) => NodeLock | null;
  
  // Utilities
  getUserColor: (userId: string) => string;
  isUserActive: (userId: string) => boolean;
}

// =============================================================================
// Default Values
// =============================================================================

const defaultState: CollaborationState = {
  session: null,
  activeUsers: [],
  comments: [],
  locks: [],
  isConnected: false,
  isJoining: false,
  connectionStatus: 'disconnected',
};

// =============================================================================
// User Colors
// =============================================================================

const USER_COLORS = [
  '#3B82F6', // Blue
  '#10B981', // Green
  '#F59E0B', // Amber
  '#EF4444', // Red
  '#8B5CF6', // Purple
  '#06B6D4', // Cyan
  '#F97316', // Orange
  '#EC4899', // Pink
  '#6B7280', // Gray
  '#84CC16', // Lime
];

// =============================================================================
// Context Creation
// =============================================================================

const CollaborationContext = createContext<CollaborationContextType | undefined>(undefined);

// =============================================================================
// Collaboration Provider Component
// =============================================================================

export const CollaborationProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [state, setState] = useState<CollaborationState>(defaultState);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [heartbeatInterval, setHeartbeatInterval] = useState<NodeJS.Timeout | null>(null);

  // WebSocket connection management
  const connectWebSocket = (workflowId: string) => {
    if (!user) return;

    const wsUrl = `ws://localhost:8000/ws/collaboration/${workflowId}`;
    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log('Collaboration WebSocket connected');
      setState(prev => ({ ...prev, isConnected: true, connectionStatus: 'connected' }));
      setReconnectAttempts(0);
      
      // Start heartbeat
      const interval = setInterval(() => {
        if (websocket.readyState === WebSocket.OPEN) {
          websocket.send(JSON.stringify({ type: 'heartbeat' }));
        }
      }, 30000);
      setHeartbeatInterval(interval);
      
      // Send join event
      websocket.send(JSON.stringify({
        type: 'join',
        userId: user.id,
        userName: user.name,
        userEmail: user.email,
        workflowId,
      }));
    };

    websocket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    websocket.onclose = () => {
      console.log('Collaboration WebSocket disconnected');
      setState(prev => ({ ...prev, isConnected: false, connectionStatus: 'disconnected' }));
      
      if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
        setHeartbeatInterval(null);
      }
      
      // Attempt reconnection
      if (reconnectAttempts < 5) {
        setTimeout(() => {
          setReconnectAttempts(prev => prev + 1);
          setState(prev => ({ ...prev, connectionStatus: 'reconnecting' }));
          connectWebSocket(workflowId);
        }, Math.pow(2, reconnectAttempts) * 1000);
      }
    };

    websocket.onerror = (error) => {
      console.error('Collaboration WebSocket error:', error);
      toast({
        title: "Connection Error",
        description: "Failed to connect to collaboration server",
        variant: "destructive",
      });
    };

    setWs(websocket);
  };

  const handleWebSocketMessage = (message: any) => {
    const { type, data } = message;

    switch (type) {
      case 'user_joined':
        setState(prev => ({
          ...prev,
          activeUsers: [...prev.activeUsers.filter(u => u.id !== data.userId), {
            id: data.userId,
            name: data.userName,
            email: data.userEmail,
            avatar: data.userAvatar,
            lastActivity: new Date().toISOString(),
            color: getUserColor(data.userId),
            isActive: true,
          }],
        }));
        
        toast({
          title: "User Joined",
          description: `${data.userName} joined the collaboration session`,
        });
        break;

      case 'user_left':
        setState(prev => ({
          ...prev,
          activeUsers: prev.activeUsers.filter(u => u.id !== data.userId),
        }));
        
        toast({
          title: "User Left",
          description: `${data.userName} left the collaboration session`,
        });
        break;

      case 'cursor_moved':
        setState(prev => ({
          ...prev,
          activeUsers: prev.activeUsers.map(user =>
            user.id === data.userId
              ? { ...user, cursor: { x: data.x, y: data.y }, lastActivity: new Date().toISOString() }
              : user
          ),
        }));
        break;

      case 'node_updated':
        // Handle node updates from other users
        // This would typically trigger a callback to update the workflow
        break;

      case 'edge_updated':
        // Handle edge updates from other users
        break;

      case 'node_locked':
        setState(prev => ({
          ...prev,
          locks: [...prev.locks.filter(l => l.nodeId !== data.nodeId), {
            nodeId: data.nodeId,
            userId: data.userId,
            userName: data.userName,
            lockedAt: data.lockedAt,
            expiresAt: data.expiresAt,
          }],
        }));
        break;

      case 'node_unlocked':
        setState(prev => ({
          ...prev,
          locks: prev.locks.filter(l => l.nodeId !== data.nodeId),
        }));
        break;

      case 'comment_added':
        setState(prev => ({
          ...prev,
          comments: [...prev.comments, data.comment],
        }));
        break;

      case 'comment_updated':
        setState(prev => ({
          ...prev,
          comments: prev.comments.map(c =>
            c.id === data.commentId ? { ...c, ...data.updates } : c
          ),
        }));
        break;

      case 'comment_deleted':
        setState(prev => ({
          ...prev,
          comments: prev.comments.filter(c => c.id !== data.commentId),
        }));
        break;

      default:
        console.log('Unknown collaboration message type:', type);
    }
  };

  // =============================================================================
  // Actions
  // =============================================================================

  const joinSession = async (workflowId: string): Promise<void> => {
    if (!user) throw new Error('User not authenticated');
    
    setState(prev => ({ ...prev, isJoining: true, connectionStatus: 'connecting' }));
    
    try {
      // Connect to WebSocket
      connectWebSocket(workflowId);
      
      // Load initial collaboration data
      const response = await fetch(`/api/collaboration/sessions/${workflowId}`);
      const sessionData = await response.json();
      
      setState(prev => ({
        ...prev,
        session: sessionData.session,
        comments: sessionData.comments,
        locks: sessionData.locks,
        isJoining: false,
      }));
    } catch (error) {
      setState(prev => ({ ...prev, isJoining: false }));
      throw error;
    }
  };

  const leaveSession = () => {
    if (ws) {
      ws.send(JSON.stringify({ type: 'leave', userId: user?.id }));
      ws.close();
      setWs(null);
    }
    
    if (heartbeatInterval) {
      clearInterval(heartbeatInterval);
      setHeartbeatInterval(null);
    }
    
    setState(defaultState);
  };

  const sendCursorPosition = (x: number, y: number) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'cursor_move',
        userId: user?.id,
        x,
        y,
      }));
    }
  };

  const sendNodeUpdate = (nodeId: string, nodeData: any) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'node_update',
        userId: user?.id,
        nodeId,
        nodeData,
      }));
    }
  };

  const sendEdgeUpdate = (edgeId: string, edgeData: any) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'edge_update',
        userId: user?.id,
        edgeId,
        edgeData,
      }));
    }
  };

  const sendSelectionChange = (selectedNodes: string[], selectedEdges: string[]) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'selection_change',
        userId: user?.id,
        selectedNodes,
        selectedEdges,
      }));
    }
  };

  // =============================================================================
  // Comments
  // =============================================================================

  const addComment = async (content: string, nodeId?: string, position?: { x: number; y: number }): Promise<Comment> => {
    const response = await fetch('/api/collaboration/comments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workflowId: state.session?.workflowId,
        nodeId,
        content,
        position,
      }),
    });
    
    const comment = await response.json();
    return comment;
  };

  const updateComment = async (commentId: string, content: string): Promise<void> => {
    await fetch(`/api/collaboration/comments/${commentId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
  };

  const deleteComment = async (commentId: string): Promise<void> => {
    await fetch(`/api/collaboration/comments/${commentId}`, {
      method: 'DELETE',
    });
  };

  const resolveComment = async (commentId: string): Promise<void> => {
    await fetch(`/api/collaboration/comments/${commentId}/resolve`, {
      method: 'POST',
    });
  };

  const replyToComment = async (commentId: string, content: string): Promise<Comment> => {
    const response = await fetch(`/api/collaboration/comments/${commentId}/replies`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    
    const reply = await response.json();
    return reply;
  };

  // =============================================================================
  // Locking
  // =============================================================================

  const lockNode = async (nodeId: string): Promise<void> => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'lock_node',
        userId: user?.id,
        userName: user?.name,
        nodeId,
      }));
    }
  };

  const unlockNode = async (nodeId: string): Promise<void> => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'unlock_node',
        userId: user?.id,
        nodeId,
      }));
    }
  };

  const isNodeLocked = (nodeId: string): boolean => {
    const lock = state.locks.find(l => l.nodeId === nodeId);
    if (!lock) return false;
    
    // Check if lock has expired
    const now = new Date();
    const expiresAt = new Date(lock.expiresAt);
    return now < expiresAt;
  };

  const getNodeLock = (nodeId: string): NodeLock | null => {
    const lock = state.locks.find(l => l.nodeId === nodeId);
    if (!lock) return null;
    
    // Check if lock has expired
    const now = new Date();
    const expiresAt = new Date(lock.expiresAt);
    return now < expiresAt ? lock : null;
  };

  // =============================================================================
  // Utilities
  // =============================================================================

  const getUserColor = (userId: string): string => {
    const hash = userId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return USER_COLORS[hash % USER_COLORS.length];
  };

  const isUserActive = (userId: string): boolean => {
    const user = state.activeUsers.find(u => u.id === userId);
    if (!user) return false;
    
    const lastActivity = new Date(user.lastActivity);
    const now = new Date();
    const timeDiff = now.getTime() - lastActivity.getTime();
    return timeDiff < 60000; // Active if last activity was within 1 minute
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      leaveSession();
    };
  }, []);

  // =============================================================================
  // Context Value
  // =============================================================================

  const contextValue: CollaborationContextType = {
    // State
    session: state.session,
    activeUsers: state.activeUsers,
    comments: state.comments,
    locks: state.locks,
    isConnected: state.isConnected,
    isJoining: state.isJoining,
    connectionStatus: state.connectionStatus,
    
    // Actions
    joinSession,
    leaveSession,
    sendCursorPosition,
    sendNodeUpdate,
    sendEdgeUpdate,
    sendSelectionChange,
    
    // Comments
    addComment,
    updateComment,
    deleteComment,
    resolveComment,
    replyToComment,
    
    // Locking
    lockNode,
    unlockNode,
    isNodeLocked,
    getNodeLock,
    
    // Utilities
    getUserColor,
    isUserActive,
  };

  return (
    <CollaborationContext.Provider value={contextValue}>
      {children}
    </CollaborationContext.Provider>
  );
};

// =============================================================================
// Custom Hook
// =============================================================================

export const useCollaboration = (): CollaborationContextType => {
  const context = useContext(CollaborationContext);
  if (context === undefined) {
    throw new Error('useCollaboration must be used within a CollaborationProvider');
  }
  return context;
};

export default CollaborationProvider;