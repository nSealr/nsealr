#!/usr/bin/env python3
"""Verify baseline repository structure for nSealr repos."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.name

COMMON_FILES = [
    "README.md",
    "LICENSE",
    "Makefile",
    ".pre-commit-config.yaml",
    "docs/architecture.md",
    "docs/testing.md",
    "docs/roadmap.md",
    "docs/audit-checklist.md",
    ".github/workflows/ci.yml",
]

REQUIRED_DIRS = {
    "specs": ["protocols", "schemas", "vectors", "examples", "docs", "scripts"],
    "companion": ["apps", "packages", "docs", "scripts"],
    "raspberry": ["app", "os", "docs", "scripts"],
    "firmware": ["crates", "apps", "ci", "boards", "docs", "scripts"],
    "smartcard": ["applet", "tools", "docs", "scripts"],
    "hardware": ["pcb", "bom", "enclosures", "docs", "scripts"],
    "website": ["content", "public", "design", "docs", "scripts"],
    "lab": ["wiki", "sources", "scripts", "docs"],
}

LICENSE_MARKERS = {
    "specs": "Creative Commons CC0",
    "lab": "Creative Commons CC0",
    "hardware": "CERN Open Hardware Licence",
}

COMPANION_PACKAGES = {
    "browser-provider": "@nsealr/browser-provider",
    "client": "@nsealr/client",
    "core": "@nsealr/core",
    "dev-signer": "@nsealr/dev-signer",
    "fixtures": "@nsealr/fixtures",
    "framing": "@nsealr/framing",
    "nip46": "@nsealr/nip46",
    "policy": "@nsealr/policy",
    "protocol": "@nsealr/protocol",
    "qr": "@nsealr/qr",
    "review": "@nsealr/review",
    "sdk": "@nsealr/sdk",
    "smartcard": "@nsealr/smartcard",
    "transport": "@nsealr/transport",
}
COMPANION_APPS = {
    "browser-extension": "@nsealr/browser-extension",
    "cli": "@nsealr/cli",
    "consumer-smoke": "@nsealr/consumer-smoke",
    "sdk-examples": "@nsealr/sdk-examples",
    "service": "@nsealr/service",
}
DEEP_SOURCE_IMPORT_RE = re.compile(r'from\s+["\'](?:\.\./){2,}[^"\']*/src/|from\s+["\'][^"\']*packages/[^"\']*/src/')
COMPANION_REPOSITORY_URL = "git+https://github.com/nSealr/companion.git"
COMPANION_BUGS_URL = "https://github.com/nSealr/companion/issues"
COMPANION_HOMEPAGE = "https://github.com/nSealr/companion#readme"


def expected_license_marker() -> str:
    return LICENSE_MARKERS.get(REPO, "MIT License")


def verify_companion_tooling(errors: list[str]) -> None:
    package_path = ROOT / "package.json"
    makefile_path = ROOT / "Makefile"
    changelog_path = ROOT / "CHANGELOG.md"
    release_path = ROOT / "docs" / "release.md"
    sdk_examples_path = ROOT / "docs" / "sdk-examples.md"
    api_docs_path = ROOT / "docs" / "api.md"
    api_review_path = ROOT / "docs" / "api-review.md"
    release_workflow_path = ROOT / ".github" / "workflows" / "package-release.yml"
    if not package_path.exists() or not makefile_path.exists():
        return

    package = json.loads(package_path.read_text(encoding="utf-8"))
    if package.get("description") != "Secretless host-side companion packages for nSealr signer integrations.":
        errors.append("package.json must document the companion workspace description")
    if package.get("license") != "MIT":
        errors.append("package.json must declare MIT license")
    if package.get("repository") != {"type": "git", "url": COMPANION_REPOSITORY_URL}:
        errors.append("package.json must point to the companion GitHub repository")
    if package.get("bugs") != {"url": COMPANION_BUGS_URL}:
        errors.append("package.json must point bugs to the companion issue tracker")
    if package.get("homepage") != COMPANION_HOMEPAGE:
        errors.append("package.json must point homepage to the companion README")
    if package.get("packageManager") != "pnpm@10.33.4":
        errors.append("package.json must pin packageManager to pnpm@10.33.4")
    scripts = package.get("scripts")
    if not isinstance(scripts, dict):
        errors.append("package.json must expose repository scripts")
    elif scripts.get("build") != "node scripts/build_packages.mjs":
        errors.append("package.json must expose the deterministic package build script")
    elif scripts.get("consumer-smoke") != "pnpm --filter @nsealr/consumer-smoke smoke":
        errors.append("package.json must expose consumer-smoke through @nsealr/consumer-smoke")
    elif scripts.get("examples-smoke") != "pnpm --filter @nsealr/sdk-examples verify":
        errors.append("package.json must expose examples-smoke through @nsealr/sdk-examples")
    elif scripts.get("readme-examples:check") != "node scripts/check_readme_examples.mjs":
        errors.append("package.json must expose README example execution")
    elif scripts.get("api-docs:check") != "node scripts/check_api_docs.mjs":
        errors.append("package.json must expose API documentation drift checks")
    elif scripts.get("api-docs:update") != "node scripts/check_api_docs.mjs --write":
        errors.append("package.json must expose API documentation regeneration")
    elif scripts.get("api-review:check") != "node scripts/check_api_review.mjs":
        errors.append("package.json must expose API review drift checks")
    elif scripts.get("package-registry:check") != "node scripts/check_package_registry.mjs":
        errors.append("package.json must expose package registry drift checks")
    elif scripts.get("browser-runtime-imports:check") != "node scripts/check_browser_runtime_imports.mjs":
        errors.append("package.json must expose browser runtime import-hygiene checks")
    elif scripts.get("browser-runtime-bundle:check") != "node scripts/check_browser_runtime_bundle.mjs":
        errors.append("package.json must expose browser runtime bundle-smoke checks")
    elif scripts.get("browser-extension-security:check") != "node scripts/check_browser_extension_security.mjs":
        errors.append("package.json must expose browser extension security checks")
    elif scripts.get("public-imports:check") != "node scripts/check_public_imports.mjs":
        errors.append("package.json must expose public import-hygiene checks")
    elif scripts.get("release-plan") != "node scripts/release_plan.mjs":
        errors.append("package.json must expose the package release plan")
    elif scripts.get("release-plan:check") != "node scripts/check_release_plan.mjs":
        errors.append("package.json must expose package release plan checks")
    elif scripts.get("pack-smoke") != "node scripts/pack_smoke.mjs":
        errors.append("package.json must expose the packed tarball smoke script")
    elif scripts.get("release-artifacts:safety") != "node scripts/check_release_artifacts_safety.mjs":
        errors.append("package.json must expose release-artifacts output safety checks")
    elif scripts.get("release-artifacts") != "node scripts/prepare_release_artifacts.mjs --out release-artifacts/packages":
        errors.append("package.json must expose release-artifacts preparation")
    elif scripts.get("ci") != "pnpm build && pnpm typecheck && pnpm test && pnpm consumer-smoke && pnpm examples-smoke && pnpm readme-examples:check && pnpm api-docs:check && pnpm api-review:check && pnpm package-registry:check && pnpm browser-runtime-imports:check && pnpm browser-runtime-bundle:check && pnpm browser-extension-security:check && pnpm public-imports:check && pnpm release-plan:check && pnpm release-artifacts:safety && pnpm pack-smoke":
        errors.append("package.json ci must build package artifacts, API review, and import-hygiene checks")

    makefile = makefile_path.read_text(encoding="utf-8")
    if "PNPM_VERSION := 10.33.4" not in makefile:
        errors.append("Makefile must declare PNPM_VERSION := 10.33.4")
    if "npm exec --yes --package=pnpm@$(PNPM_VERSION) -- pnpm" not in makefile:
        errors.append("Makefile must provide a pinned npm exec fallback for pnpm")
    if "build:" not in makefile or "$(PNPM) build" not in makefile:
        errors.append("Makefile must build package artifacts before tests")
    if "package-smoke:" not in makefile or "$(PNPM) consumer-smoke" not in makefile:
        errors.append("Makefile must run the public package consumer smoke")
    if "examples-smoke:" not in makefile or "$(PNPM) examples-smoke" not in makefile:
        errors.append("Makefile must run the SDK examples smoke")
    if "readme-examples:" not in makefile or "$(PNPM) readme-examples:check" not in makefile:
        errors.append("Makefile must run package README examples")
    if "api-docs:" not in makefile or "$(PNPM) api-docs:check" not in makefile:
        errors.append("Makefile must run the API documentation drift check")
    if "api-docs-update:" not in makefile or "$(PNPM) api-docs:update" not in makefile:
        errors.append("Makefile must expose API documentation regeneration")
    if "api-review:" not in makefile or "$(PNPM) api-review:check" not in makefile:
        errors.append("Makefile must run the API review drift check")
    if "package-registry:" not in makefile or "$(PNPM) package-registry:check" not in makefile:
        errors.append("Makefile must run the package registry drift check")
    if "browser-runtime-imports:" not in makefile or "$(PNPM) browser-runtime-imports:check" not in makefile:
        errors.append("Makefile must run the browser runtime import-hygiene check")
    if "browser-runtime-bundle:" not in makefile or "$(PNPM) browser-runtime-bundle:check" not in makefile:
        errors.append("Makefile must run the browser runtime bundle-smoke check")
    if "browser-extension-security:" not in makefile or "$(PNPM) browser-extension-security:check" not in makefile:
        errors.append("Makefile must run the browser extension security check")
    if "public-imports:" not in makefile or "$(PNPM) public-imports:check" not in makefile:
        errors.append("Makefile must run the public import-hygiene check")
    if "release-plan:" not in makefile or "$(PNPM) release-plan" not in makefile:
        errors.append("Makefile must render the package release plan")
    if "release-plan-check:" not in makefile or "$(PNPM) release-plan:check" not in makefile:
        errors.append("Makefile must run package release plan checks")
    if "release-artifacts-safety:" not in makefile or "$(PNPM) release-artifacts:safety" not in makefile:
        errors.append("Makefile must run release artifact output safety checks")
    if "pack-smoke:" not in makefile or "$(PNPM) pack-smoke" not in makefile:
        errors.append("Makefile must run the packed tarball smoke")
    if "release-artifacts:" not in makefile or "$(PNPM) release-artifacts" not in makefile:
        errors.append("Makefile must prepare release artifacts")
    if "ci:" not in makefile or "browser-runtime-imports" not in makefile.split("ci:", 1)[1].splitlines()[0]:
        errors.append("Makefile ci must include the browser runtime import-hygiene check")
    if "ci:" not in makefile or "package-registry" not in makefile.split("ci:", 1)[1].splitlines()[0]:
        errors.append("Makefile ci must include the package registry drift check")
    if "ci:" not in makefile or "browser-runtime-bundle" not in makefile.split("ci:", 1)[1].splitlines()[0]:
        errors.append("Makefile ci must include the browser runtime bundle-smoke check")
    if "ci:" not in makefile or "browser-extension-security" not in makefile.split("ci:", 1)[1].splitlines()[0]:
        errors.append("Makefile ci must include the browser extension security check")
    if "ci:" not in makefile or "release-artifacts-safety" not in makefile.split("ci:", 1)[1].splitlines()[0]:
        errors.append("Makefile ci must include the release artifact output safety check")
    if "ci:" not in makefile or "release-plan-check" not in makefile.split("ci:", 1)[1].splitlines()[0]:
        errors.append("Makefile ci must include the package release plan check")

    if not changelog_path.exists() or "## Unreleased" not in changelog_path.read_text(encoding="utf-8"):
        errors.append("CHANGELOG.md must track unreleased package changes")
    for rel in [
        "scripts/package_set.mjs",
        "scripts/check_package_registry.mjs",
        "scripts/release_plan.mjs",
        "scripts/check_release_plan.mjs",
        "scripts/prepare_release_artifacts.mjs",
        "scripts/check_release_artifacts_safety.mjs",
    ]:
        if not (ROOT / rel).exists():
            errors.append(f"missing companion package release helper: {rel}")
    release_artifacts_text = (ROOT / "scripts" / "prepare_release_artifacts.mjs").read_text(encoding="utf-8")
    for marker in [
        "buildCompanionPackageReleasePlan",
        "companionPackageReleasePlanDigest",
        "release_plan_digest",
    ]:
        if marker not in release_artifacts_text:
            errors.append(f"release artifact helper must bind artifacts to release plan marker: {marker}")
    if not (ROOT / "scripts" / "check_api_docs.mjs").exists():
        errors.append("missing companion API documentation drift helper: scripts/check_api_docs.mjs")
    if not (ROOT / "scripts" / "check_api_review.mjs").exists():
        errors.append("missing companion API review drift helper: scripts/check_api_review.mjs")
    if not (ROOT / "scripts" / "check_package_registry.mjs").exists():
        errors.append("missing companion package registry drift helper: scripts/check_package_registry.mjs")
    if not (ROOT / "scripts" / "check_browser_runtime_imports.mjs").exists():
        errors.append("missing companion browser runtime import-hygiene helper: scripts/check_browser_runtime_imports.mjs")
    if not (ROOT / "scripts" / "check_browser_runtime_bundle.mjs").exists():
        errors.append("missing companion browser runtime bundle-smoke helper: scripts/check_browser_runtime_bundle.mjs")
    if not (ROOT / "scripts" / "check_browser_extension_security.mjs").exists():
        errors.append("missing companion browser extension security helper: scripts/check_browser_extension_security.mjs")
    if not (ROOT / "scripts" / "check_readme_examples.mjs").exists():
        errors.append("missing companion README example drift helper: scripts/check_readme_examples.mjs")
    if not release_path.exists():
        errors.append("docs/release.md must document release policy")
    else:
        release_text = release_path.read_text(encoding="utf-8")
        if "npm publish --provenance" not in release_text or "make integration" not in release_text:
            errors.append("docs/release.md must document provenance and integration release gates")
        if "release_plan_digest" not in release_text:
            errors.append("docs/release.md must document release artifact manifest plan binding")
    if not sdk_examples_path.exists():
        errors.append("docs/sdk-examples.md must document executable SDK examples")
    else:
        sdk_examples_text = sdk_examples_path.read_text(encoding="utf-8")
        if "make examples-smoke" not in sdk_examples_text or "@nsealr/sdk-examples" not in sdk_examples_text:
            errors.append("docs/sdk-examples.md must document make examples-smoke and @nsealr/sdk-examples")
        if "import every publishable public" not in sdk_examples_text:
            errors.append("docs/sdk-examples.md must document full public-package import coverage")
        if "make readme-examples" not in sdk_examples_text or "nsealr-readme-example" not in sdk_examples_text:
            errors.append("docs/sdk-examples.md must document executable package README snippets")
    if not api_docs_path.exists():
        errors.append("docs/api.md must document the public package API surface")
    else:
        api_docs_text = api_docs_path.read_text(encoding="utf-8")
        for package_name in COMPANION_PACKAGES.values():
            if package_name == "@nsealr/dev-signer":
                continue
            if f"## {package_name}" not in api_docs_text:
                errors.append(f"docs/api.md must document {package_name}")
    if not api_review_path.exists():
        errors.append("docs/api-review.md must record the reviewed public package API surface")
    else:
        api_review_text = api_review_path.read_text(encoding="utf-8")
        if "API surface digest:" not in api_review_text:
            errors.append("docs/api-review.md must bind the review to docs/api.md")
        for package_name in COMPANION_PACKAGES.values():
            if package_name == "@nsealr/dev-signer":
                continue
            if f"## {package_name}" not in api_review_text:
                errors.append(f"docs/api-review.md must review {package_name}")
    if not release_workflow_path.exists():
        errors.append(".github/workflows/package-release.yml must document package release rehearsal")
    else:
        release_workflow = release_workflow_path.read_text(encoding="utf-8")
        for marker in [
            "Package Release Rehearsal",
            "workflow_dispatch:",
            "make ci",
            "make release-plan",
            "make release-artifacts",
            "actions/upload-artifact@v6",
            "FORCE_JAVASCRIPT_ACTIONS_TO_NODE24"
        ]:
            if marker not in release_workflow:
                errors.append(f"package release rehearsal workflow must include {marker}")
        if "npm publish" in release_workflow:
            errors.append("package release rehearsal workflow must not publish to npm")


def read_json(path: Path, errors: list[str]) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        errors.append(f"invalid JSON in {path.relative_to(ROOT)}: {error}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.relative_to(ROOT)} must contain a JSON object")
        return {}
    return value


def verify_companion_package_boundaries(errors: list[str]) -> None:
    root_package = read_json(ROOT / "package.json", errors)
    for package_dir, package_name in COMPANION_PACKAGES.items():
        package_root = ROOT / "packages" / package_dir
        package_json_path = package_root / "package.json"
        readme_path = package_root / "README.md"
        index_path = package_root / "src" / "index.ts"
        if not package_json_path.exists():
            errors.append(f"missing package manifest: packages/{package_dir}/package.json")
            continue
        if not readme_path.exists():
            errors.append(f"missing package README: packages/{package_dir}/README.md")
        else:
            readme_text = readme_path.read_text(encoding="utf-8")
            if "## Boundary" not in readme_text:
                errors.append(f"packages/{package_dir}/README.md must document the package boundary")
            if package_dir != "dev-signer" and "nsealr-readme-example" not in readme_text:
                errors.append(f"packages/{package_dir}/README.md must include an executable README example")
        if not index_path.exists():
            errors.append(f"missing package entrypoint: packages/{package_dir}/src/index.ts")
        package = read_json(package_json_path, errors)
        if package.get("name") != package_name:
            errors.append(f"packages/{package_dir}/package.json must be named {package_name}")
        description = package.get("description")
        if not isinstance(description, str) or not description:
            errors.append(f"packages/{package_dir}/package.json must declare a package description")
        keywords = package.get("keywords")
        if (
            not isinstance(keywords, list)
            or "nostr" not in keywords
            or "nsealr" not in keywords
            or "signer" not in keywords
        ):
            errors.append(f"packages/{package_dir}/package.json must declare core npm keywords")
        if package.get("license") != "MIT":
            errors.append(f"packages/{package_dir}/package.json must declare MIT license")
        if package.get("sideEffects") is not False:
            errors.append(f"packages/{package_dir}/package.json must declare sideEffects=false")
        if package.get("repository") != {
            "type": "git",
            "url": COMPANION_REPOSITORY_URL,
            "directory": f"packages/{package_dir}",
        }:
            errors.append(f"packages/{package_dir}/package.json must point to its repository directory")
        if package.get("bugs") != {"url": COMPANION_BUGS_URL}:
            errors.append(f"packages/{package_dir}/package.json must point bugs to the companion issue tracker")
        if package.get("homepage") != COMPANION_HOMEPAGE:
            errors.append(f"packages/{package_dir}/package.json must point homepage to the companion README")
        if package.get("version") != root_package.get("version"):
            errors.append(f"packages/{package_dir}/package.json must use the synchronized root package version")
        if package_dir == "dev-signer":
            if package.get("private") is not True:
                errors.append("packages/dev-signer/package.json must remain private")
            if "publishConfig" in package:
                errors.append("packages/dev-signer/package.json must not declare public publishConfig")
        elif package.get("private") is True:
            errors.append(f"packages/{package_dir}/package.json must be publishable when release gates open")
        elif package.get("publishConfig") != {"access": "public", "provenance": True}:
            errors.append(f"packages/{package_dir}/package.json must declare public provenance publishConfig")
        if package.get("type") != "module":
            errors.append(f"packages/{package_dir}/package.json must declare type=module")
        if package.get("files") != ["dist", "README.md"]:
            errors.append(f"packages/{package_dir}/package.json must publish only dist and README.md")
        exports = package.get("exports")
        if not isinstance(exports, dict):
            errors.append(f"packages/{package_dir}/package.json must declare explicit exports")
        else:
            root_export = exports.get(".")
            if (
                not isinstance(root_export, dict)
                or root_export.get("types") != "./dist/index.d.ts"
                or root_export.get("import") != "./dist/index.js"
            ):
                errors.append(f"packages/{package_dir}/package.json must export built dist entrypoints")
            if package_dir == "fixtures":
                specs_root_export = exports.get("./specs-root")
                if (
                    not isinstance(specs_root_export, dict)
                    or specs_root_export.get("types") != "./dist/specs-root.d.ts"
                    or specs_root_export.get("import") != "./dist/specs-root.js"
                ):
                    errors.append("packages/fixtures/package.json must export built specs-root entrypoint")
        if package.get("types") != "./dist/index.d.ts":
            errors.append(f"packages/{package_dir}/package.json must expose ./dist/index.d.ts types")
        if package_dir != "dev-signer":
            for dependency_section in [
                "dependencies",
                "devDependencies",
                "peerDependencies",
                "optionalDependencies",
                "bundleDependencies",
                "bundledDependencies",
            ]:
                dependency_value = package.get(dependency_section)
                if isinstance(dependency_value, dict) and "@nsealr/dev-signer" in dependency_value:
                    errors.append(
                        f"packages/{package_dir} must not reference test-only @nsealr/dev-signer in {dependency_section}"
                    )
                if isinstance(dependency_value, list) and "@nsealr/dev-signer" in dependency_value:
                    errors.append(
                        f"packages/{package_dir} must not reference test-only @nsealr/dev-signer in {dependency_section}"
                    )

    for app_dir, package_name in COMPANION_APPS.items():
        package_json_path = ROOT / "apps" / app_dir / "package.json"
        if not package_json_path.exists():
            errors.append(f"missing app manifest: apps/{app_dir}/package.json")
            continue
        package = read_json(package_json_path, errors)
        if package.get("name") != package_name:
            errors.append(f"apps/{app_dir}/package.json must be named {package_name}")

    sdk_examples_package = read_json(ROOT / "apps" / "sdk-examples" / "package.json", errors)
    sdk_examples_dependencies = sdk_examples_package.get("dependencies")
    sdk_examples_source = ROOT / "apps" / "sdk-examples" / "src" / "index.ts"
    sdk_examples_text = sdk_examples_source.read_text(encoding="utf-8") if sdk_examples_source.exists() else ""
    for package_dir, package_name in COMPANION_PACKAGES.items():
        if package_dir == "dev-signer":
            continue
        if not isinstance(sdk_examples_dependencies, dict) or package_name not in sdk_examples_dependencies:
            errors.append(f"apps/sdk-examples/package.json must depend on {package_name}")
        if f'from "{package_name}"' not in sdk_examples_text:
            errors.append(f"apps/sdk-examples/src/index.ts must import {package_name}")

    for source_path in [*ROOT.glob("packages/*/src/**/*.ts"), *ROOT.glob("apps/*/src/**/*.ts")]:
        text = source_path.read_text(encoding="utf-8")
        if DEEP_SOURCE_IMPORT_RE.search(text):
            errors.append(
                f"{source_path.relative_to(ROOT)} must import other packages through @nsealr/* entrypoints"
            )


def main() -> int:
    errors: list[str] = []

    for rel in COMMON_FILES:
        path = ROOT / rel
        if not path.exists():
            errors.append(f"missing required file: {rel}")
        elif path.is_file() and not path.read_text(encoding="utf-8").strip():
            errors.append(f"empty required file: {rel}")

    for rel in REQUIRED_DIRS.get(REPO, []):
        if not (ROOT / rel).is_dir():
            errors.append(f"missing required directory: {rel}")

    license_path = ROOT / "LICENSE"
    if license_path.exists():
        license_text = license_path.read_text(encoding="utf-8", errors="replace")
        marker = expected_license_marker()
        if marker not in license_text:
            errors.append(f"LICENSE does not contain expected marker: {marker}")

    readme = ROOT / "README.md"
    if readme.exists():
        readme_text = readme.read_text(encoding="utf-8")
        if "## License" not in readme_text:
            errors.append("README.md must include a License section")

    if REPO == "companion":
        verify_companion_tooling(errors)
        verify_companion_package_boundaries(errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"nSealr {REPO} baseline verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
