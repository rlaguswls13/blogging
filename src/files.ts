import { readFile, writeFile } from "node:fs/promises";
import { RunStateSchema, type RunState } from "./types.js";

export async function readJson<T>(filePath: string): Promise<T> {
  return JSON.parse(await readFile(filePath, "utf8")) as T;
}

export async function writeJson(filePath: string, value: unknown): Promise<void> {
  await writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

export async function readState(filePath: string): Promise<RunState> {
  return RunStateSchema.parse(await readJson(filePath));
}

