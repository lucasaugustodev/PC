import { Router } from "express";
import bcrypt from "bcryptjs";
import { eq } from "drizzle-orm";
import { loginSchema, registerSchema } from "@hiveclip/shared";
import { users } from "@hiveclip/db";
import { signToken, requireAuth } from "../middleware/auth.js";
import type { Db } from "../app.js";

export function createAuthRouter(db: Db) {
  const router = Router();

  router.post("/register", async (req, res) => {
    const data = registerSchema.parse(req.body);
    const existing = await db.select().from(users).where(eq(users.email, data.email)).limit(1);
    if (existing.length > 0) {
      res.status(409).json({ error: "Email already registered" });
      return;
    }
    const passwordHash = await bcrypt.hash(data.password, 10);
    const [user] = await db.insert(users).values({
      email: data.email,
      passwordHash,
      displayName: data.displayName ?? null,
      role: "user",
    }).returning();
    const token = signToken({ id: user.id, email: user.email, role: user.role! });
    res.status(201).json({
      token,
      user: { id: user.id, email: user.email, displayName: user.displayName, role: user.role, createdAt: user.createdAt?.toISOString() },
    });
  });

  router.post("/login", async (req, res) => {
    const data = loginSchema.parse(req.body);
    const [user] = await db.select().from(users).where(eq(users.email, data.email)).limit(1);
    if (!user || !(await bcrypt.compare(data.password, user.passwordHash))) {
      res.status(401).json({ error: "Invalid credentials" });
      return;
    }
    const token = signToken({ id: user.id, email: user.email, role: user.role! });
    res.json({
      token,
      user: { id: user.id, email: user.email, displayName: user.displayName, role: user.role, createdAt: user.createdAt?.toISOString() },
    });
  });

  router.get("/me", requireAuth, async (req, res) => {
    const [user] = await db.select().from(users).where(eq(users.id, req.user!.id)).limit(1);
    if (!user) { res.status(404).json({ error: "User not found" }); return; }
    res.json({ id: user.id, email: user.email, displayName: user.displayName, role: user.role, createdAt: user.createdAt?.toISOString() });
  });

  return router;
}
