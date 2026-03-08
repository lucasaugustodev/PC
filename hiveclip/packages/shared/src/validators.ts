import { z } from "zod";

export const createBoardSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().optional(),
});

export const updateBoardSchema = z.object({
  name: z.string().min(1).max(100).optional(),
  description: z.string().optional(),
  brandColor: z.string().regex(/^#[0-9a-fA-F]{6}$/).optional(),
});

export const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
});

export const registerSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  displayName: z.string().min(1).max(100).optional(),
});

export type CreateBoardInput = z.infer<typeof createBoardSchema>;
export type UpdateBoardInput = z.infer<typeof updateBoardSchema>;
export type LoginInput = z.infer<typeof loginSchema>;
export type RegisterInput = z.infer<typeof registerSchema>;
