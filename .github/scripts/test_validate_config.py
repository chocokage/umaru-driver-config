#!/usr/bin/env python3
"""
Self-test for validate_config.py.

A validator that never fails is the same as no validator, and this one guards the
file that controls every installed copy of the app. So each rule is checked
against a document that should break it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_config import validate  # noqa: E402


def good() -> dict:
    return {
        "minVersion": "1.0.0",
        "iosStoreUrl": "https://apps.apple.com/us/app/driver-exam/id123456789",
        "androidStoreUrl": "https://play.google.com/store/apps/details?id=com.vincenttu91.driver_exam",
        "maintenanceMode": False,
        "maintenanceMessage": "",
        "featureFlags": {
            "gamesEnabled": True,
            "aiTutorEnabled": True,
            "pushNotificationsEnabled": True,
            "weeklySprintEnabled": True,
            "diagnosticQuizEnabled": True,
        },
    }


CASES: list[tuple[str, dict, bool]] = []


def case(name: str, mutate, should_fail: bool = True) -> None:
    cfg = good()
    mutate(cfg)
    CASES.append((name, cfg, should_fail))


# A clean document must pass, or every other assertion here is meaningless.
case("a well-formed config", lambda c: None, should_fail=False)

# The bug this whole system exists to prevent: a truthy string silently
# blacking out the app, or silently failing to.
case("maintenanceMode as the string 'false'", lambda c: c.update(maintenanceMode="false"))
case("maintenanceMode as the string 'true'", lambda c: c.update(maintenanceMode="true"))
case("maintenanceMode as a number", lambda c: c.update(maintenanceMode=1))

# Turning the app off with no explanation, behind a modal nobody can dismiss.
case(
    "maintenance on with no message",
    lambda c: c.update(maintenanceMode=True, maintenanceMessage="   "),
)
case(
    "maintenance on with a message",
    lambda c: c.update(maintenanceMode=True, maintenanceMessage="Back at 09:00 UTC."),
    should_fail=False,
)

case("minVersion missing a patch part", lambda c: c.update(minVersion="1.2"))
case("minVersion with a v prefix", lambda c: c.update(minVersion="v1.2.0"))
case("minVersion as a number", lambda c: c.update(minVersion=1))

case("overlong maintenance message", lambda c: c.update(maintenanceMessage="x" * 301))
case("maintenance message at the limit", lambda c: c.update(maintenanceMessage="x" * 300), should_fail=False)

# The update button is the only way out of an undismissable modal, so it must
# never be redirectable.
case("ios store url off-host", lambda c: c.update(iosStoreUrl="https://evil.example/phish"))
case(
    "android store url on a lookalike host",
    lambda c: c.update(androidStoreUrl="https://play.google.com.evil.example/x"),
)
case("empty ios store url is allowed", lambda c: c.update(iosStoreUrl=""), should_fail=False)

case("non-boolean feature flag", lambda c: c["featureFlags"].update(gamesEnabled="yes"))
case("featureFlags as a list", lambda c: c.update(featureFlags=[]))

# Not fatal -- the app ignores unknown keys and defaults missing ones to on --
# but both are almost always typos, so they must warn.
case("unknown feature flag", lambda c: c["featureFlags"].update(gamesEnabeld=True), should_fail=False)
case("missing feature flag", lambda c: c["featureFlags"].pop("gamesEnabled"), should_fail=False)


def main() -> int:
    failures = 0

    for name, cfg, should_fail in CASES:
        errors, _ = validate(cfg)
        failed = bool(errors)
        if failed != should_fail:
            want = "rejected" if should_fail else "accepted"
            got = "rejected" if failed else "accepted"
            print(f"FAIL  {name}: expected {want}, was {got}")
            for err in errors:
                print(f"        {err}")
            failures += 1
        else:
            print(f"ok    {name}")

    # Warnings are the only signal for typos, so prove they actually fire.
    _, warn_unknown = validate(
        {**good(), "featureFlags": {**good()["featureFlags"], "gamesEnabeld": True}}
    )
    if not any("gamesEnabeld" in w for w in warn_unknown):
        print("FAIL  an unknown feature flag produced no warning")
        failures += 1
    else:
        print("ok    an unknown feature flag warns")

    _, warn_missing = validate({**good(), "featureFlags": {}})
    if not any("default to on" in w for w in warn_missing):
        print("FAIL  missing feature flags produced no warning")
        failures += 1
    else:
        print("ok    missing feature flags warn")

    print()
    if failures:
        print(f"{failures} self-test failure(s).")
        return 1
    print(f"All {len(CASES) + 2} validator self-tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
