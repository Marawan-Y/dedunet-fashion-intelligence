# Mobile PoC

1. Start the API from the repository root.
2. Copy the mobile environment file:
   - Android emulator: `EXPO_PUBLIC_API_BASE=http://10.0.2.2:8000`
   - iOS simulator: `EXPO_PUBLIC_API_BASE=http://127.0.0.1:8000`
   - Physical phone: use the development computer's LAN IP.
3. Run `npm install` and `npx expo start`.

The package versions are a snapshot for the PoC. Before production, regenerate with the current stable Expo SDK and run Expo's dependency alignment command.
