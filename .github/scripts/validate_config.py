#!/usr/bin/env python3
"""
Validate config.json against the rules the app actually applies.

The app is deliberately forgiving: anything it does not understand is dropped and
the compiled-in default is used instead. That means a bad edit here does not
crash anything -- it silently does nothing, which during an incident is the worst
possible failure. This script turns that silence into a failed check.

Mirrors `parseRemoteConfig` in constants/stores/remoteConfigStore.ts.
"""

import json
import re
import sys
from pathlib import Path

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
MAX_MAINTENANCE_MESSAGE = 300
IOS_STORE_HOST = "https://apps.apple.com/"
ANDROID_STORE_HOST = "https://play.google.com/"

# Flags the app knows about. An unknown flag is not fatal -- the app ignores it --
# but it is almost always a typo, so say so loudly.
KNOWN_FLAGS = {
    "gamesEnabled",
    "aiTutorEnabled",
    "pushNotificationsEnabled",
    "weeklySprintEnabled",
    "diagnosticQuizEnabled",
}

def validate(cfg: dict) -> tuple[list[str], list[str]]:
    """Pure check. Returns (errors, warnings) so it can be self-tested."""
    errors: list[str] = []
    warnings: list[str] = []
    _check_min_version(cfg, errors)
    _check_maintenance(cfg, errors)
    _check_store_urls(cfg, errors, warnings)
    _check_flags(cfg, errors, warnings)
    return errors, warnings


def main() -> int:
    path = Path(__file__).resolve().parents[2] / "config.json"

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"FAIL  cannot read {path}: {exc}")
        return 1

    try:
        cfg = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"FAIL  config.json is not valid JSON: {exc}")
        print("      Every client would fall back to its built-in defaults.")
        return 1

    if not isinstance(cfg, dict):
        print("FAIL  config.json must be a JSON object.")
        return 1

    errors, warnings = validate(cfg)

    for warning in warnings:
        print(f"WARN  {warning}")
    for error in errors:
        print(f"FAIL  {error}")

    if errors:
        print(f"\n{len(errors)} problem(s). The app would ignore these fields.")
        return 1

    print("OK    config.json is valid and every field would be applied.")
    return 0


def _check_min_version(cfg: dict, errors: list) -> None:
    value = cfg.get("minVersion")
    if not isinstance(value, str) or not SEMVER.match(value):
        errors.append(
            f"minVersion must be exactly 'X.Y.Z' (got {value!r}). "
            "'1.2' and 'v1.2.0' are both rejected by the app."
        )


def _check_maintenance(cfg: dict, errors: list) -> None:
    mode = cfg.get("maintenanceMode")
    if not isinstance(mode, bool):
        errors.append(
            f"maintenanceMode must be a real boolean (got {mode!r}). "
            'Quoted "true"/"false" is ignored by the app.'
        )

    message = cfg.get("maintenanceMessage")
    if not isinstance(message, str):
        errors.append(f"maintenanceMessage must be a string (got {message!r}).")
    elif len(message) > MAX_MAINTENANCE_MESSAGE:
        errors.append(
            f"maintenanceMessage is {len(message)} characters; "
            f"the app truncates at {MAX_MAINTENANCE_MESSAGE}."
        )

    # Turning the app off without saying why leaves users staring at a modal
    # they cannot dismiss.
    if mode is True and not (isinstance(message, str) and message.strip()):
        errors.append(
            "maintenanceMode is on but maintenanceMessage is empty. "
            "The modal cannot be dismissed, so tell users what is happening."
        )


def _check_store_urls(cfg: dict, errors: list, warnings: list) -> None:
    for field, host in (("iosStoreUrl", IOS_STORE_HOST), ("androidStoreUrl", ANDROID_STORE_HOST)):
        value = cfg.get(field)
        if not isinstance(value, str):
            errors.append(f"{field} must be a string (got {value!r}).")
        elif value and not value.startswith(host):
            errors.append(
                f"{field} must start with {host} (got {value!r}). "
                "The app drops anything else so the update button cannot be redirected."
            )

    if cfg.get("iosStoreUrl") == "":
        warnings.append(
            "iosStoreUrl is empty. The iOS force-update button stays disabled "
            "until the app is listed on the App Store."
        )


def _check_flags(cfg: dict, errors: list, warnings: list) -> None:
    flags = cfg.get("featureFlags")
    if not isinstance(flags, dict):
        errors.append(f"featureFlags must be an object (got {flags!r}).")
        return

    for key, value in flags.items():
        if not isinstance(value, bool):
            errors.append(f"featureFlags.{key} must be a boolean (got {value!r}).")
        if key not in KNOWN_FLAGS:
            warnings.append(
                f"featureFlags.{key} is not a flag the app reads; it will be ignored. "
                f"Known flags: {', '.join(sorted(KNOWN_FLAGS))}."
            )

    missing = KNOWN_FLAGS - set(flags)
    if missing:
        warnings.append(
            f"Not listed, so they default to on: {', '.join(sorted(missing))}."
        )


if __name__ == "__main__":
    sys.exit(main())
