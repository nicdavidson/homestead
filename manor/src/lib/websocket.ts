function getWsUrl(): string {
  if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL;
  const host = typeof window !== "undefined" ? window.location.hostname : "localhost";
  return `ws://${host}:8700`;
}

const WS_URL = getWsUrl();
const RECONNECT_DELAY_MS = 2000;
const MAX_RECONNECT_DELAY_MS = 30000;

interface ChatCallbacks {
  onDelta: (text: string) => void;
  onResult: (fullText: string) => void;
  onError: (error: string) => void;
  onClose: () => void;
  onOpen?: () => void;
}

let ws: WebSocket | null = null;
let callbacks: ChatCallbacks | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectDelay = RECONNECT_DELAY_MS;
let intentionalClose = false;

function attachListeners(socket: WebSocket, cb: ChatCallbacks) {
  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "delta") {
        cb.onDelta(data.text ?? data.content ?? "");
      } else if (data.type === "result") {
        cb.onResult(data.text ?? data.content ?? "");
      } else if (data.type === "error") {
        cb.onError(data.message || "Unknown error");
      }
    } catch {
      cb.onDelta(event.data);
    }
  };

  socket.onerror = () => {
    // Don't surface transient errors — onclose handles reconnect
  };

  socket.onopen = () => {
    reconnectDelay = RECONNECT_DELAY_MS;
    cb.onOpen?.();
  };

  socket.onclose = () => {
    cb.onClose();
    if (!intentionalClose) {
      scheduleReconnect();
    }
  };
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  if (!callbacks) return;

  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    if (!callbacks) return;

    try {
      ws = new WebSocket(`${WS_URL}/ws/chat`);
      attachListeners(ws, callbacks);
    } catch {
      reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY_MS);
      scheduleReconnect();
    }
  }, reconnectDelay);

  reconnectDelay = Math.min(reconnectDelay * 1.5, MAX_RECONNECT_DELAY_MS);
}

export function createChatConnection(cb: ChatCallbacks): WebSocket {
  intentionalClose = false;
  callbacks = cb;

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.close();
  }
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  ws = new WebSocket(`${WS_URL}/ws/chat`);
  attachListeners(ws, cb);
  return ws;
}

export function sendMessage(
  sessionName: string,
  chatId: number,
  message: string
) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    throw new Error("WebSocket is not connected");
  }
  ws.send(
    JSON.stringify({
      session_name: sessionName,
      chat_id: chatId,
      message,
    })
  );
}

export function disconnect() {
  intentionalClose = true;
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (ws) {
    ws.close();
    ws = null;
  }
  callbacks = null;
}
