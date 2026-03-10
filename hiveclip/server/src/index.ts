import "dotenv/config";
import pino from "pino";
import { createApp } from "./app.js";
import { startDb, stopDb } from "./db.js";
import { setupVncProxy } from "./vnc-proxy.js";
import { setupLauncherWsProxy } from "./launcher-proxy.js";

const logger = pino({
  transport: {
    target: "pino-pretty",
    options: { colorize: true },
  },
});

const PORT = Number(process.env.PORT) || 3100;

async function main() {
  logger.info("Starting embedded PostgreSQL...");
  const { db } = await startDb();
  logger.info("PostgreSQL ready");

  const app = createApp(logger, db);

  const server = app.listen(PORT, () => {
    logger.info(`HiveClip Control Plane listening on port ${PORT}`);
  });

  setupVncProxy(server);
  setupLauncherWsProxy(server);
  logger.info("VNC + Launcher WebSocket proxies ready");

  async function shutdown() {
    logger.info("Shutting down gracefully...");
    server.close(async () => {
      await stopDb();
      logger.info("Server closed");
      process.exit(0);
    });
  }

  process.on("SIGTERM", shutdown);
  process.on("SIGINT", shutdown);
}

main().catch((err) => {
  logger.error(err, "Failed to start");
  process.exit(1);
});
