#!/usr/bin/env node
import { readFileSync, writeSync } from "node:fs";
import { verifyBrowserExtensionPackageBuildDirectory } from "./package-build.js";

type PackageVerifyCliOptions = {
  buildResultPath?: string;
  packagePlanReviewPath?: string;
};

function takeOptionValue(args: string[], index: number, option: string): string {
  const value = args[index + 1];
  if (value === undefined || value.startsWith("--")) {
    throw new Error(`${option} requires a value`);
  }
  return value;
}

function parsePackageVerifyArgs(args: string[]): PackageVerifyCliOptions {
  const normalizedArgs = args[0] === "--" ? args.slice(1) : args;
  const options: PackageVerifyCliOptions = {};
  for (let index = 0; index < normalizedArgs.length; index += 1) {
    const arg = normalizedArgs[index];
    if (arg === "--build-result") {
      if (options.buildResultPath !== undefined) {
        throw new Error("--build-result must be specified only once");
      }
      options.buildResultPath = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else if (arg === "--package-plan-review") {
      if (options.packagePlanReviewPath !== undefined) {
        throw new Error("--package-plan-review must be specified only once");
      }
      options.packagePlanReviewPath = takeOptionValue(normalizedArgs, index, arg);
      index += 1;
    } else {
      throw new Error(`unsupported browser-extension package-verify option: ${arg}`);
    }
  }
  return options;
}

function readJsonFile(path: string, label: string): unknown {
  const contents = readFileSync(path, "utf8");
  try {
    return JSON.parse(contents);
  } catch (error) {
    throw new Error(`${label} JSON is invalid: ${error instanceof Error ? error.message : String(error)}`);
  }
}

export async function browserExtensionPackageVerifyJsonFromArgs(args: string[]): Promise<string> {
  const options = parsePackageVerifyArgs(args);
  if (options.buildResultPath === undefined) {
    throw new Error("--build-result is required");
  }
  if (options.packagePlanReviewPath === undefined) {
    throw new Error("--package-plan-review is required");
  }
  const result = await verifyBrowserExtensionPackageBuildDirectory(
    readJsonFile(options.buildResultPath, "browser extension package build result"),
    {
      packagePlanReview: readJsonFile(
        options.packagePlanReviewPath,
        "browser extension package-plan review"
      )
    }
  );
  return `${JSON.stringify(result, null, 2)}\n`;
}

export async function runBrowserExtensionPackageVerifyCli(args: string[]): Promise<void> {
  try {
    writeSync(1, await browserExtensionPackageVerifyJsonFromArgs(args));
  } catch (error) {
    writeSync(2, `${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 1;
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  await runBrowserExtensionPackageVerifyCli(process.argv.slice(2));
}
