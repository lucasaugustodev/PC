import { Router } from "express";
import { eq, and } from "drizzle-orm";
import { createBoardSchema, updateBoardSchema } from "@hiveclip/shared";
import { boards } from "@hiveclip/db";
import { requireAuth } from "../middleware/auth.js";
import type { Db } from "../app.js";

function generatePrefix(name: string): string {
  const words = name.trim().split(/\s+/);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  return name.slice(0, 3).toUpperCase();
}

export function createBoardsRouter(db: Db) {
  const router = Router();

  router.get("/", requireAuth, async (req, res) => {
    const result = await db.select().from(boards).where(eq(boards.ownerId, req.user!.id));
    res.json(result);
  });

  router.post("/", requireAuth, async (req, res) => {
    const data = createBoardSchema.parse(req.body);
    const [board] = await db.insert(boards).values({
      ownerId: req.user!.id,
      name: data.name,
      description: data.description ?? null,
      status: "provisioning",
      issuePrefix: generatePrefix(data.name) + "-" + Date.now().toString(36).slice(-3).toUpperCase(),
    }).returning();
    res.status(201).json(board);
  });

  router.get("/:id", requireAuth, async (req, res) => {
    const [board] = await db.select().from(boards).where(
      and(eq(boards.id, req.params.id), eq(boards.ownerId, req.user!.id))
    ).limit(1);
    if (!board) { res.status(404).json({ error: "Board not found" }); return; }
    res.json(board);
  });

  router.patch("/:id", requireAuth, async (req, res) => {
    const data = updateBoardSchema.parse(req.body);
    const updates: Record<string, unknown> = { updatedAt: new Date() };
    if (data.name) updates.name = data.name;
    if (data.description !== undefined) updates.description = data.description ?? null;
    if (data.brandColor !== undefined) updates.brandColor = data.brandColor ?? null;

    const [board] = await db.update(boards)
      .set(updates)
      .where(and(eq(boards.id, req.params.id), eq(boards.ownerId, req.user!.id)))
      .returning();
    if (!board) { res.status(404).json({ error: "Board not found" }); return; }
    res.json(board);
  });

  router.delete("/:id", requireAuth, async (req, res) => {
    const [board] = await db.delete(boards)
      .where(and(eq(boards.id, req.params.id), eq(boards.ownerId, req.user!.id)))
      .returning();
    if (!board) { res.status(404).json({ error: "Board not found" }); return; }
    res.status(204).end();
  });

  return router;
}
