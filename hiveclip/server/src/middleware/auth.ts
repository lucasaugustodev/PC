import type { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import { unauthorized } from "./error-handler.js";

const JWT_SECRET = process.env.JWT_SECRET || "hiveclip-dev-secret";

export function signToken(payload: { id: string; email: string; role: string }): string {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: "7d" });
}

function extractToken(req: Request): string | null {
  const header = req.headers.authorization;
  if (header?.startsWith("Bearer ")) return header.slice(7);
  return null;
}

export function requireAuth(req: Request, _res: Response, next: NextFunction) {
  const token = extractToken(req);
  if (!token) throw unauthorized("Missing auth token");
  try {
    const decoded = jwt.verify(token, JWT_SECRET) as { id: string; email: string; role: string };
    req.user = decoded;
    next();
  } catch {
    throw unauthorized("Invalid token");
  }
}

export function optionalAuth(req: Request, _res: Response, next: NextFunction) {
  const token = extractToken(req);
  if (token) {
    try {
      req.user = jwt.verify(token, JWT_SECRET) as { id: string; email: string; role: string };
    } catch { /* ignore */ }
  }
  next();
}
