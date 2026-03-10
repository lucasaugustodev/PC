import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema/index.js";

export function createDb(url: string) {
  const sql = postgres(url);
  const db = drizzle(sql, { schema });
  return { db, sql };
}
