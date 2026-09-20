# umaru-driver-config

Runtime configuration for the **Driver Exam** app (`com.vincenttu91.driver_exam`).

The app fetches [`config.json`](config.json) once on every launch, straight from
`raw.githubusercontent.com`. There is no server involved — editing this file and
pushing to `main` is how you force an update or take the app offline.

```
https://raw.githubusercontent.com/chocokage/umaru-driver-config/main/config.json
```

> **This repo controls every installed copy of the app.** `maintenanceMode` shows a
> modal the user *cannot dismiss*. Treat write access here like production access,
> because it is.

## `config.json`

| Field | Type | Effect |
| --- | --- | --- |
| `minVersion` | `"X.Y.Z"` | Apps older than this get a blocking update modal. Must be exactly three numeric parts. |
| `iosStoreUrl` | string | Where the update button sends iOS users. Must be on `apps.apple.com`. Empty until the app is listed. |
| `androidStoreUrl` | string | Same for Android. Must be on `play.google.com`. |
| `maintenanceMode` | bool | `true` shows an undismissable maintenance modal. **Real boolean — `"true"` in quotes is ignored.** |
| `maintenanceMessage` | string | Shown in that modal. Truncated to 300 characters. |
| `featureFlags` | `{string: bool}` | Per-feature kill switches. Non-boolean values are dropped. |

### Feature flags

Turning one off hides that feature's entry points. The rest of the app is
unaffected, so this is the safe way to shut down one broken thing instead of the
whole app.

| Flag | Turns off |
| --- | --- |
| `gamesEnabled` | The games hub and its tiles on Home and More |
| `aiTutorEnabled` | The AI Tutor tile (this one calls a paid API — kill it first if costs spike) |
| `pushNotificationsEnabled` | Scheduling of study reminders |
| `weeklySprintEnabled` | The Weekly Sprint tile |
| `diagnosticQuizEnabled` | The diagnostic quiz tile |

## Runbook

### Force everyone onto a new version

Ship the build to both stores **first and wait until it is actually downloadable**,
then raise `minVersion`. Raising it before the build is live locks users out with
an update button that leads to the old version.

```jsonc
"minVersion": "1.1.0"
```

### Take the app down during an incident

```jsonc
"maintenanceMode": true,
"maintenanceMessage": "We're fixing a problem with question downloads. Back by 09:00 UTC."
```

Write the message for a nervous user the day before their road test: say what is
broken and when it will be back. Set it to `false` to bring everyone back.

### Disable one broken feature

```jsonc
"featureFlags": { "aiTutorEnabled": false }
```

## How long changes take to land

`raw.githubusercontent.com` caches for about **five minutes**, and the app only
reads this on launch. So expect up to ~5 minutes plus however long until the user
next opens the app. It is not instant — during an incident, set it early.

## Safety properties

The client is deliberately distrustful of this file, so a mistake here degrades
rather than bricks:

- **Only this exact repo path is accepted.** `raw.githubusercontent.com` serves
  every public repo on GitHub, so the app pins the full
  `/chocokage/umaru-driver-config/main/` prefix, not just the host.
- **No credentials are sent.** This is public static JSON on someone else's
  infrastructure; the app's API key is never attached to this request.
- **Fields are validated, never coerced.** A wrong type is ignored and the built-in
  default is used. `"maintenanceMode": "false"` is a *string*, and a naive
  implementation would treat it as truthy and black out the app — here it is simply
  dropped.
- **Store URLs are host-checked** against `apps.apple.com` / `play.google.com`, so
  this file cannot redirect users somewhere arbitrary.
- **Failures are silent.** Bad JSON, a 404, or no network means the app keeps its
  compiled-in defaults and starts normally. The fetch is abandoned after 8 seconds
  so a hung request can never delay launch.

## Before you push

```bash
python3 -m json.tool config.json    # valid JSON?
```

A syntax error here is not catastrophic — clients will fail to parse it and fall
back to defaults — but it does mean your intended change silently does nothing.

## Related

Same pattern as [`citizen-exam-config`](https://github.com/chocokage/citizen-exam-config)
and [`umaru-caro-config`](https://github.com/chocokage/umaru-caro-config).
