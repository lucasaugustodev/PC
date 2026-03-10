import type { Request, Response, Router } from "express";
import { Router as createRouter } from "express";
import type { Server as HttpServer } from "node:http";
import http from "node:http";
import { WebSocketServer, WebSocket } from "ws";
import jwt from "jsonwebtoken";
import crypto from "node:crypto";

const JWT_SECRET = process.env.JWT_SECRET || "hiveclip-dev-secret";
const LAUNCHER_PORT = 3001;

// Session tokens: maps sessionId -> expiry timestamp
const sessions = new Map<string, number>();

function parseCookies(header: string | undefined): Record<string, string> {
  if (!header) return {};
  return Object.fromEntries(header.split(";").map(c => c.trim().split("=").map(s => s.trim())));
}

/**
 * HTTP reverse proxy: /api/launcher/:ip/* -> http://<ip>:3001/*
 */
export function createLauncherRouter(): Router {
  const router = createRouter();

  function proxyHandler(req: Request, res: Response) {
    const vmIp = req.params.ip as string;
    if (!/^\d+\.\d+\.\d+\.\d+$/.test(vmIp)) {
      res.status(400).json({ error: "Invalid IP" });
      return;
    }

    // Verify JWT from Authorization header, query param, or session cookie
    const authHeader = req.headers.authorization;
    const queryToken = req.query.token as string | undefined;
    const token = authHeader?.startsWith("Bearer ") ? authHeader.slice(7) : queryToken || null;
    const cookies = parseCookies(req.headers.cookie);
    const sessionId = cookies["launcher_session"];

    let authenticated = false;

    // Check JWT token first
    if (token) {
      try {
        jwt.verify(token, JWT_SECRET);
        authenticated = true;
      } catch { /* invalid token */ }
    }

    // Fall back to session cookie
    if (!authenticated && sessionId) {
      const expiry = sessions.get(sessionId);
      if (expiry && expiry > Date.now()) {
        authenticated = true;
      } else {
        sessions.delete(sessionId);
      }
    }

    if (!authenticated) {
      res.status(401).json({ error: "Unauthorized" });
      return;
    }

    // If authenticated via JWT, create/refresh a session cookie for sub-requests (CSS/JS/etc)
    if (token) {
      const sid = crypto.randomBytes(24).toString("hex");
      sessions.set(sid, Date.now() + 3600_000); // 1 hour
      res.setHeader("Set-Cookie", `launcher_session=${sid}; Path=/api/launcher/${vmIp}; HttpOnly; SameSite=Lax; Max-Age=3600`);
    }

    // Build target URL — *path param is an array in path-to-regexp@8
    const rawPath = (req.params as Record<string, string | string[]>).path;
    const subPath = Array.isArray(rawPath) ? rawPath.join("/") : rawPath || "";
    const url = new URL(req.url!, `http://${req.headers.host}`);
    url.searchParams.delete("token");
    const qs = url.searchParams.toString();
    const fullUrl = `http://${vmIp}:${LAUNCHER_PORT}/${subPath}${qs ? "?" + qs : ""}`;

    const proxyReq = http.request(
      fullUrl,
      {
        method: req.method,
        headers: { ...req.headers, host: `${vmIp}:${LAUNCHER_PORT}` },
        timeout: 30_000,
      },
      (proxyRes) => {
        res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
        proxyRes.pipe(res);
      },
    );

    proxyReq.on("error", (err) => {
      console.error(`[Launcher Proxy] HTTP error for ${vmIp}:`, err.message);
      if (!res.headersSent) {
        res.status(502).json({ error: `Launcher unreachable: ${err.message}` });
      }
    });

    // If express.json() already parsed the body, we need to re-serialize it
    // because the original stream was consumed
    if (req.body && typeof req.body === "object" && Object.keys(req.body).length > 0) {
      const bodyStr = JSON.stringify(req.body);
      proxyReq.setHeader("content-length", Buffer.byteLength(bodyStr));
      proxyReq.end(bodyStr);
    } else {
      req.pipe(proxyReq);
    }
  }

  // Handle both root and subpaths
  router.all("/:ip", proxyHandler);
  router.all("/:ip/*path", proxyHandler);

  return router;
}

/**
 * WebSocket proxy for the launcher's terminal:
 * ws://host/api/launcher-ws/:ip?token=...  ->  ws://<ip>:3001
 */
export function setupLauncherWsProxy(server: HttpServer) {
  const wss = new WebSocketServer({ noServer: true });

  const existingListeners = server.listeners("upgrade").slice();
  server.removeAllListeners("upgrade");

  server.on("upgrade", (req, socket, head) => {
    console.log(`[Launcher WS] Upgrade request: ${req.url}`);
    // Match both /api/launcher-ws/:ip and /api/launcher/:ip/ws (iframe path)
    const matchDedicated = req.url?.match(/^\/api\/launcher-ws\/(\d+\.\d+\.\d+\.\d+)/);
    const matchInline = req.url?.match(/^\/api\/launcher\/(\d+\.\d+\.\d+\.\d+)\/ws/);
    const match = matchDedicated || matchInline;
    console.log(`[Launcher WS] matchDedicated=${!!matchDedicated}, matchInline=${!!matchInline}`);
    if (!match) {
      console.log(`[Launcher WS] No match, passing to ${existingListeners.length} existing listeners`);
      for (const listener of existingListeners) {
        (listener as Function).call(server, req, socket, head);
      }
      return;
    }

    const url = new URL(req.url!, `http://${req.headers.host}`);
    const token = url.searchParams.get("token");
    console.log(`[Launcher WS] IP=${match[1]}, hasToken=${!!token}`);

    // Also check session cookie for auth (iframe sub-requests)
    const cookieHeader = req.headers.cookie;
    const cookies = cookieHeader ? Object.fromEntries(cookieHeader.split(";").map(c => c.trim().split("=").map(s => s.trim()))) : {};
    const sessionId = cookies["launcher_session"];

    let authenticated = false;
    if (token) {
      try { jwt.verify(token, JWT_SECRET); authenticated = true; } catch {}
    }
    if (!authenticated && sessionId) {
      const expiry = sessions.get(sessionId);
      if (expiry && expiry > Date.now()) authenticated = true;
    }

    console.log(`[Launcher WS] Auth: token=${!!token ? 'jwt' : 'none'}, session=${!!sessionId}, authenticated=${authenticated}`);
    if (!authenticated) {
      console.log(`[Launcher WS] 401 Unauthorized - rejecting`);
      socket.write("HTTP/1.1 401 Unauthorized\r\n\r\n");
      socket.destroy();
      return;
    }

    const vmIp = match[1];

    wss.handleUpgrade(req, socket, head, (clientWs) => {
      // For inline path, strip /api/launcher/IP prefix and forward the rest
      // For dedicated path, strip /api/launcher-ws/IP prefix
      const stripPattern = matchDedicated
        ? /^\/api\/launcher-ws\/\d+\.\d+\.\d+\.\d+/
        : /^\/api\/launcher\/\d+\.\d+\.\d+\.\d+/;
      const vmWsPath = req.url?.replace(stripPattern, "") || "";
      const vmWsUrl = `ws://${vmIp}:${LAUNCHER_PORT}${vmWsPath}`;
      console.log(`[Launcher WS] Connecting to VM: ${vmWsUrl}`);
      const vmWs = new WebSocket(vmWsUrl);

      vmWs.on("open", () => {
        console.log(`[Launcher WS] Connected to ${vmIp}:${LAUNCHER_PORT}`);
      });

      vmWs.on("message", (data, isBinary) => {
        if (clientWs.readyState === WebSocket.OPEN) clientWs.send(data, { binary: isBinary });
      });

      clientWs.on("message", (data, isBinary) => {
        if (vmWs.readyState === WebSocket.OPEN) vmWs.send(data, { binary: isBinary });
      });

      vmWs.on("error", (err) => {
        console.error(`[Launcher WS] VM error:`, err.message);
        clientWs.close(1011, "Launcher connection error");
      });

      vmWs.on("close", () => clientWs.close());
      clientWs.on("close", () => vmWs.close());
      clientWs.on("error", () => vmWs.close());
    });
  });

  return wss;
}
