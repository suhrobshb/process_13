import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Enumeration of WebSocket connection states for clarity and consistency.
 */
export const ReadyState = {
  UNINSTANTIATED: -1,
  CONNECTING: 0,
  OPEN: 1,
  CLOSING: 2,
  CLOSED: 3,
};

/**
 * Configuration options for the useWebSocket hook.
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
  /** The maximum number of retry attempts before giving up. Defaults to 5. */
  maxRetries?: number;
  /** The base interval for retries in milliseconds, using exponential backoff. Defaults to 2000. */
  retryInterval?: number;
}

/**
 * An advanced React hook to manage WebSocket connections with robust features:
 * - **Automatic Reconnection**: Automatically tries to reconnect on disconnection with exponential backoff.
 * - **Message Queuing**: Queues messages sent while the connection is down and sends them upon reconnection.
 * - **State Management**: Provides the current connection state (connecting, open, closed, etc.).
 *
 * @param url The WebSocket URL to connect to. If the URL is `null`, the connection will be closed.
 * @param options Configuration options for the WebSocket connection.
 * @returns An object containing the connection's `readyState`, the `lastMessage` received,
 *          and a `sendMessage` function.
 */
export const useWebSocket = (url: string | null, options: WebSocketOptions = {}) => {
  const {
    onOpen,
    onClose,
    onError,
    onMessage,
    retryOnError = true,
    maxRetries = 5,
    retryInterval = 2000,
  } = options;

  const [lastMessage, setLastMessage] = useState<WebSocketEventMap['message'] | null>(null);
  const [readyState, setReadyState] = useState<number>(ReadyState.UNINSTANTIATED);
  
  // Use a ref to store the message queue to avoid re-triggering the effect.
  const messageQueueRef = useRef<(string | ArrayBufferLike | Blob | ArrayBufferView)[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef<number>(0);

  /**
   * A memoized function to send data to the WebSocket server.
   * If the connection is open, it sends the message immediately.
   * If the connection is not open, it queues the message to be sent automatically
   * once the connection is established.
   */
  const sendMessage = useCallback((data: string | ArrayBufferLike | Blob | ArrayBufferView) => {
    if (wsRef.current && wsRef.current.readyState === ReadyState.OPEN) {
      wsRef.current.send(data);
    } else {
      messageQueueRef.current.push(data);
      console.warn('useWebSocket: WebSocket is not open. Message has been queued.');
    }
  }, []);

  useEffect(() => {
    // If the URL is null, we close the connection and do nothing.
    if (url === null) {
      if (wsRef.current) {
        setReadyState(ReadyState.CLOSING);
        wsRef.current.close();
      }
      return;
    }

    let connectAttemptTimer: NodeJS.Timeout;

    const connect = () => {
      // Prevent multiple concurrent connection attempts.
      if (wsRef.current && wsRef.current.readyState !== ReadyState.CLOSED) {
        return;
      }

      setReadyState(ReadyState.CONNECTING);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = (event) => {
        console.log('useWebSocket: Connection opened.');
        setReadyState(ReadyState.OPEN);
        retryCountRef.current = 0; // Reset retry count on successful connection.
        
        // Send any messages that were queued while the connection was down.
        if (messageQueueRef.current.length > 0) {
          console.log(`useWebSocket: Sending ${messageQueueRef.current.length} queued messages.`);
          messageQueueRef.current.forEach(msg => ws.send(msg));
          messageQueueRef.current = []; // Clear the queue.
        }
        
        if (onOpen) onOpen(event);
      };

      ws.onmessage = (event) => {
        setLastMessage(event);
        if (onMessage) onMessage(event);
      };

      ws.onclose = (event) => {
        wsRef.current = null;
        // Only attempt to reconnect if the close was not intentional.
        if (readyState !== ReadyState.CLOSING) {
            setReadyState(ReadyState.CLOSED);
            if (onClose) onClose(event);

            // Automatic reconnection logic with exponential backoff.
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
        // The `onclose` event is fired automatically by the browser after an error,
        // which will then trigger the reconnection logic if enabled.
      };
    };

    connect();

    // Cleanup function: This is called when the component unmounts or when the URL changes.
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
  // The effect should re-run only if the URL or the callback options change.
  // Using `useRef` for the queue prevents this from re-running on every `sendMessage` call.
  }, [url, onOpen, onClose, onError, onMessage, retryOnError, maxRetries, retryInterval]);

  return { sendMessage, lastMessage, readyState };
};
