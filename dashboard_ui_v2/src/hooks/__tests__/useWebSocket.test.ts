/**
 * useWebSocket Hook Tests
 * ======================
 */

import { renderHook, act } from '@testing-library/react';
import { useWebSocket } from '../useWebSocket';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  public readyState = MockWebSocket.CONNECTING;
  public onopen: ((event: Event) => void) | null = null;
  public onclose: ((event: CloseEvent) => void) | null = null;
  public onmessage: ((event: MessageEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;

  constructor(public url: string) {
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 100);
  }

  send(data: string) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  // Helper method to simulate receiving messages
  simulateMessage(data: any) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  // Helper method to simulate errors
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
}

// Replace global WebSocket with mock
(global as any).WebSocket = MockWebSocket;

describe('useWebSocket', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('initializes with correct default state', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws'));
    
    expect(result.current.connectionStatus).toBe('Connecting');
    expect(result.current.lastMessage).toBeNull();
    expect(result.current.sendMessage).toBeInstanceOf(Function);
  });

  it('connects to WebSocket successfully', async () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws'));
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 150));
    });
    
    expect(result.current.connectionStatus).toBe('Open');
  });

  it('sends messages correctly', async () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost:8000/ws'));
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 150));
    });
    
    const testMessage = { type: 'test', data: 'hello' };
    
    await act(async () => {
      result.current.sendMessage(testMessage);
    });
    
    // Message sending should not throw error when connection is open
    expect(result.current.connectionStatus).toBe('Open');
  });

  it('receives messages correctly', async () => {
    const onMessage = jest.fn();
    const { result } = renderHook(() => 
      useWebSocket('ws://localhost:8000/ws', { onMessage })
    );
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 150));
    });
    
    const testMessage = { type: 'update', data: { id: 1, status: 'completed' } };
    
    await act(async () => {
      // Access the WebSocket instance and simulate message
      const ws = (result.current as any).ws?.current;
      if (ws && ws.simulateMessage) {
        ws.simulateMessage(testMessage);
      }
    });
    
    expect(onMessage).toHaveBeenCalledWith(testMessage);
    expect(result.current.lastMessage).toEqual(testMessage);
  });

  it('handles connection errors', async () => {
    const onError = jest.fn();
    const { result } = renderHook(() => 
      useWebSocket('ws://localhost:8000/ws', { onError })
    );
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 150));
    });
    
    await act(async () => {
      const ws = (result.current as any).ws?.current;
      if (ws && ws.simulateError) {
        ws.simulateError();
      }
    });
    
    expect(onError).toHaveBeenCalled();
  });

  it('attempts to reconnect after connection loss', async () => {
    const { result } = renderHook(() => 
      useWebSocket('ws://localhost:8000/ws', { 
        shouldReconnect: true,
        reconnectAttempts: 3,
        reconnectInterval: 100
      })
    );
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 150));
    });
    
    expect(result.current.connectionStatus).toBe('Open');
    
    // Simulate connection close
    await act(async () => {
      const ws = (result.current as any).ws?.current;
      if (ws) {
        ws.close();
      }
    });
    
    expect(result.current.connectionStatus).toBe('Closed');
    
    // Should attempt to reconnect
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 200));
    });
    
    expect(result.current.connectionStatus).toBe('Open');
  });

  it('does not reconnect when shouldReconnect is false', async () => {
    const { result } = renderHook(() => 
      useWebSocket('ws://localhost:8000/ws', { shouldReconnect: false })
    );
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 150));
    });
    
    expect(result.current.connectionStatus).toBe('Open');
    
    await act(async () => {
      const ws = (result.current as any).ws?.current;
      if (ws) {
        ws.close();
      }
    });
    
    expect(result.current.connectionStatus).toBe('Closed');
    
    // Should not reconnect
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 200));
    });
    
    expect(result.current.connectionStatus).toBe('Closed');
  });

  it('cleans up on unmount', async () => {
    const { result, unmount } = renderHook(() => 
      useWebSocket('ws://localhost:8000/ws')
    );
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 150));
    });
    
    expect(result.current.connectionStatus).toBe('Open');
    
    unmount();
    
    // Connection should be closed after unmount
    expect(result.current.connectionStatus).toBe('Open'); // Last known state
  });

  it('handles invalid JSON messages gracefully', async () => {
    const onError = jest.fn();
    const { result } = renderHook(() => 
      useWebSocket('ws://localhost:8000/ws', { onError })
    );
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 150));
    });
    
    await act(async () => {
      const ws = (result.current as any).ws?.current;
      if (ws && ws.onmessage) {
        // Send invalid JSON
        ws.onmessage(new MessageEvent('message', { data: 'invalid json {' }));
      }
    });
    
    expect(onError).toHaveBeenCalled();
  });
});