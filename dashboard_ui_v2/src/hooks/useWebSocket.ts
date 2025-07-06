import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Enumeration of WebSocket connection states.
 */
export const ReadyState = {
  UNINSTANTIATED: -1,
  CONNECTING: 0,
  OPEN: 1,
  CLOSING: 2,
  CLOSED: 3,
};

/**
 * Options for configuring the useWebSocket hook.
 */
export interface WebSocketOptions {
  /** Callback for when the connection is successfully opened. */
  onOpen?: (event: WebSocketEventMap['open']) => void;
  /** Callback for when the connection is closed. */
  onClose?: (event: WebSocketEventMap['close']) => void;
  /** Callback for when a connection error occurs. */
  onError?: (event: WebSocketEventMap['error']) => void;
  /** Callback for when a message is received from the server. */
  onMessage?: (event: WebSocketEventMap['message']) => void;
  /** Enables automatic reconnection on error. Defaults to true. */
  retryOnError?: boolean;
  /** The maximum number of retry attempts. Defaults to 5. */
  maxRetries?: number;
  /** The base interval for retries in milliseconds. Defaults to 2000. */
  retryInterval?: number;
}

/**
 * A custom React hook to manage WebSocket connections with support for state
 * management, message handling, and automatic reconnection.
 *
 * @param url The WebSocket URL to connect to. If null, the connection is not attempted.
 * @param options Configuration options for the WebSocket connection.
 * @returns An object containing the connection's readyState, the last received message,
 *          and a function to send messages.
 */
export const useWebSocket = (url: string | null, options: WebSocketOptions = {}) => {
  const {
    onOpen,
    onClose,
    onError,
    onMessage,
    retryOnError = true,
    maxRetries = 5,
    retryInterval = 2000, // 2 seconds base interval
  } = options;

  const [lastMessage, setLastMessage] = useState<WebSocketEventMap['message'] | null>(null);
  const [readyState, setReadyState] = useState<number>(ReadyState.UNINSTANTIATED);
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef<number>(0);

  /**
   * A memoized function to send data to the WebSocket server.
   * It only sends data if the connection is currently open.
   */
  const sendMessage = useCallback((data: string | ArrayBufferLike | Blob | ArrayBufferView) => {
    if (wsRef.current && wsRef.current.readyState === ReadyState.OPEN) {
      wsRef.current.send(data);
    } else {
      console.warn('useWebSocket: WebSocket is not open. Message not sent.');
    }
  }, []);

  useEffect(() => {
    if (url === null) {
      setReadyState(ReadyState.CLOSED);
      return;
    }

    let connectAttemptTimer: NodeJS.Timeout;

    const connect = () => {
      // Prevent multiple connection attempts
      if (wsRef.current && wsRef.current.readyState !== ReadyState.CLOSED) {
        return;
      }

      setReadyState(ReadyState.CONNECTING);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = (event) => {
        console.log('useWebSocket: Connection opened.');
        setReadyState(ReadyState.OPEN);
        retryCountRef.current = 0; // Reset retry count on successful connection
        if (onOpen) onOpen(event);
      };

      ws.onmessage = (event) => {
        setLastMessage(event);
        if (onMessage) onMessage(event);
      };

      ws.onclose = (event) => {
        wsRef.current = null;
        if (readyState !== ReadyState.CLOSING) { // Avoid retrying on intentional close
            setReadyState(ReadyState.CLOSED);
            if (onClose) onClose(event);

            // Attempt to reconnect if retry is enabled
            if (retryOnError && retryCountRef.current < maxRetries) {
                const timeout = retryInterval * Math.pow(2, retryCountRef.current);
                console.log(`useWebSocket: Connection closed. Retrying in ${timeout / 1000}s...`);
                connectAttemptTimer = setTimeout(connect, timeout);
                retryCountRef.current++;
            } else {
                console.log('useWebSocket: Max retries reached or retry is disabled.');
            }
        }
      };

      ws.onerror = (event) => {
        console.error('useWebSocket: WebSocket error:', event);
        if (onError) onError(event);
        // The `onclose` event will be fired automatically after an error,
        // which will then handle the reconnection logic.
      };
    };

    connect();

    // Cleanup function to be called on component unmount or when URL changes
    return () => {
      if (connectAttemptTimer) {
        clearTimeout(connectAttemptTimer);
      }
      if (wsRef.current) {
        setReadyState(ReadyState.CLOSING);
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [url, onOpen, onClose, onError, onMessage, retryOnError, maxRetries, retryInterval]);

  return { sendMessage, lastMessage, readyState };
};
