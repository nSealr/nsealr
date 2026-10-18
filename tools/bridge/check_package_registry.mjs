#!/usr/bin/env node
import { assertCompanionPackageRegistry, privatePackages, publicPackages } from "./package_set.mjs";

assertCompanionPackageRegistry();

console.log(
  `companion package registry passed (${publicPackages.length} public, ${privatePackages.length} private)`
);
