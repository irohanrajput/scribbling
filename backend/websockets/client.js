let ws = new WebSocket("ws://localhost:8000");

ws.onmessage = async (message) => {
  const payload = await Promise.resolve(message.data);
  console.log("we received the message from server", payload);
};

const sendMessage = async () => {
  if (ws.readyState !== WebSocket.OPEN) {
    await new Promise((resolve, reject) => {
      ws.onopen = resolve;
      ws.onerror = reject;
    });
  }

  ws.send("yohhoooo");
};

sendMessage().catch((err) => console.error("send failed:", err));
