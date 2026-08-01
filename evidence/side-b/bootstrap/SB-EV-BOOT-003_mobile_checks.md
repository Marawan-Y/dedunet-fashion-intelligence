# Side B Mobile Check Evidence

- Artifact ID: SB-EV-BOOT-003
- Version: 1.0.0
- Owner: Side B Platform Lead
- Source inputs/dependencies: `platform/poc/mobile/package.json`, `platform/poc/mobile/App.tsx`, npm registry
- Acceptance criteria: manifest scripts are inventoried and dependency installation completes before any mobile build/static claim.
- Validation procedure/result: `npm run` passed; `npm install` timed out in sandbox then failed with a reproducible dependency conflict when network access was approved.
- Evidence path: `evidence/side-b/bootstrap/SB-EV-BOOT-003_mobile_checks.md`
- Readiness status: BLOCKED
- Downstream consumer: SB-AR-B2-001; B10 future work
- Remaining risks/next action: approve a coherent Expo compatibility set, update manifest and lockfile in a separate change cycle, then run Expo dependency alignment, TypeScript, export/build, and device checks.

Working directory: `platform/poc/mobile`

```text
COMMAND: cmd /c npm run
Lifecycle scripts included in fashion-commerce-mobile-poc@0.1.0:
  start
    expo start
available via `npm run`:
  android
    expo start --android
  ios
    expo start --ios
  web
    expo start --web
EXIT_CODE: 0
```

Initial sandboxed dependency install:

```text
COMMAND: cmd /c npm install
RESULT: command timed out
EXIT_CODE: 124
WALL_TIME: 121 seconds
```

Approved network retry:

```text
COMMAND: cmd /c npm install
EXIT_CODE: 1
npm error code ERESOLVE
npm error ERESOLVE unable to resolve dependency tree
npm error
npm error While resolving: fashion-commerce-mobile-poc@0.1.0
npm error Found: react@19.1.0
npm error node_modules/react
npm error   react@"19.1.0" from the root project
npm error   peer react@"*" from expo-status-bar@3.0.9
npm error   node_modules/expo-status-bar
npm error     expo-status-bar@"~3.0.8" from the root project
npm error
npm error Could not resolve dependency:
npm error peer react@"^19.1.1" from react-native@0.82.0
npm error node_modules/react-native
npm error   react-native@"0.82.0" from the root project
npm error   peer react-native@"*" from expo-status-bar@3.0.9
npm error   node_modules/expo-status-bar
npm error     expo-status-bar@"~3.0.8" from the root project
npm error
npm error Fix the upstream dependency conflict, or retry this command with --force or --legacy-peer-deps to accept an incorrect (and potentially broken) dependency resolution.
```

No `npm --force` or `--legacy-peer-deps` workaround was used because that would mask the untouched baseline defect. No mobile build, Expo start, export, TypeScript, emulator, or device success is claimed.
