import express from "express";
import pinoHttp from "pino-http";
import type { Logger } from "pino";
import type { PostgresJsDatabase } from "drizzle-orm/postgres-js";
import type * as schema from "@hiveclip/db";
import { healthRouter } from "./routes/health.js";
import { createAuthRouter } from "./routes/auth.js";
import { createBoardsRouter } from "./routes/boards.js";
import { createVmsRouter } from "./routes/vms.js";
import { errorHandler } from "./middleware/error-handler.js";
import { startProvisioningWorker } from "./provisioner.js";
import { createLauncherRouter } from "./launcher-proxy.js";

export type Db = PostgresJsDatabase<typeof schema>;

export function createApp(logger: Logger, db: Db) {
  const app = express();

  app.use(pinoHttp({ logger, autoLogging: { ignore: (req) => req.url === "/api/health" } }));
  app.use(express.json());

  const provisioner = startProvisioningWorker(db);

  app.use("/api/health", healthRouter);
  app.use("/api/auth", createAuthRouter(db));
  app.use("/api/boards", createBoardsRouter(db));
  app.use("/api", createVmsRouter(db, provisioner));
  app.use("/api/launcher", createLauncherRouter());

  app.use(errorHandler);

  return app;
}
