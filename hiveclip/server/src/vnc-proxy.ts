import type { Server as HttpServer } from "node:http";
import { WebSocketServer, WebSocket } from "ws";
import { Socket } from "node:net";
import jwt from "jsonwebtoken";

const JWT_SECRET = process.env.JWT_SECRET || "hiveclip-dev-secret";
const VNC_PORT = 5900;

export function setupVncProxy(server: HttpServer) {
  const wss = new WebSocketServer({ noServer: true });

  server.on("upgrade", (req, socket, head) => {
    // Match /api/vnc/:ip
    const match = req.url?.match(/^\/api\/vnc\/(\d+\.\d+\.\d+\.\d+)/);
    if (!match) return;

    // Check auth from query param
    const url = new URL(req.url!, `http://${req.headers.host}`);
    const token = url.searchParams.get("token");
    if (!token) {
      socket.write("HTTP/1.1 401 Unauthorized\r\n\r\n");
      socket.destroy();
      return;
    }

    try {
      jwt.verify(token, JWT_SECRET);
    } catch {
      socket.write("HTTP/1.1 401 Unauthorized\r\n\r\n");
      socket.destroy();
      return;
    }

    const vmIp = match[1];

    wss.handleUpgrade(req, socket, head, (ws) => {
      wss.emit("connection", ws, req, vmIp);
    });
  });

  wss.on("connection", (ws: WebSocket, _req: unknown, vmIp: string) => {
    console.log(`[VNC Proxy] Connecting to ${vmIp}:${VNC_PORT}`);

    const tcp = new Socket();

    tcp.connect(VNC_PORT, vmIp, () => {
      console.log(`[VNC Proxy] Connected to ${vmIp}:${VNC_PORT}`);
    });

    tcp.on("data", (data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data);
      }
    });

    ws.on("message", (data: Buffer) => {
      if (tcp.writable) {
        tcp.write(data);
      }
    });

    tcp.on("error", (err) => {
      console.error(`[VNC Proxy] TCP error for ${vmIp}:`, err.message);
      ws.close(1011, "VNC connection error");
    });

    tcp.on("close", () => {
      console.log(`[VNC Proxy] TCP closed for ${vmIp}`);
      ws.close();
    });

    ws.on("close", () => {
      console.log(`[VNC Proxy] WebSocket closed for ${vmIp}`);
      tcp.destroy();
    });

    ws.on("error", (err) => {
      console.error(`[VNC Proxy] WS error:`, err.message);
      tcp.destroy();
    });
  });

  return wss;
}
