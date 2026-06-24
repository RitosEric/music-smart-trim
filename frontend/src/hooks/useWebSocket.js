import { useState, useEffect, useRef, useCallback } from "react";
import { io } from "socket.io-client";

const WEBSOCKET_URL = process.env.REACT_APP_WS_URL || "http://localhost:5002";

/**
 * Custom hook for WebSocket connection.
 */
export function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const socketRef = useRef(null);

  useEffect(() => {
    // Flag to prevent cleanup during React StrictMode double-invoke
    let isCleanup = false;

    // Initialize socket connection
    const socket = io(WEBSOCKET_URL, {
      transports: ["websocket"],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5,
    });

    socketRef.current = socket;

    socket.on("connect", () => {
      console.log("WebSocket connected");
      if (!isCleanup) {
        setConnected(true);
      }
    });

    socket.on("disconnect", () => {
      console.log("WebSocket disconnected");
      if (!isCleanup) {
        setConnected(false);
      }
    });

    socket.on("connected", (data) => {
      console.log("Server confirmed connection:", data);
    });

    socket.on("progress_update", (data) => {
      console.log("Progress update:", data);
      if (!isCleanup) {
        setLastMessage(data);
      }
    });

    // Cleanup on unmount
    return () => {
      isCleanup = true;
      socket.disconnect();
    };
  }, []);

  const joinJob = useCallback(
    (jobId) => {
      if (socketRef.current && connected) {
        socketRef.current.emit("join_job", { job_id: jobId });
      }
    },
    [connected],
  );

  const leaveJob = useCallback(
    (jobId) => {
      if (socketRef.current && connected) {
        socketRef.current.emit("leave_job", { job_id: jobId });
      }
    },
    [connected],
  );

  return {
    socket: socketRef.current,
    connected,
    lastMessage,
    joinJob,
    leaveJob,
  };
}

export default useWebSocket;
