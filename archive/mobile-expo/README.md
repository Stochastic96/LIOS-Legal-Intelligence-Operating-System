LIOS Mobile (Expo)

Quick start

1. Install Expo CLI (if not already):

```bash
npm install -g expo-cli
```

2. From this folder:

```bash
cd mobile-expo
npm install
expo start
```

3. Open the project in Expo Go on your phone, or use the web/Android/iOS simulator.

Configuration

- Open the app and go to Settings (first run). Set `LIOS Base URL` to your machine IP (e.g. `http://192.168.1.10:8000`) and optionally set an `API Key`.
- The app stores these values in AsyncStorage and the `src/api.js` client reads them at runtime.

Notes about networking

- When running on a physical phone, use your computer LAN IP (not `localhost`).
- You can also use Expo's tunnel option to avoid networking issues.

Files created

- `App.js` — main app with navigation and screens: Home, Chat, NextQuestion, Settings.
- `src/api.js` — API client that reads saved base URL and API key from AsyncStorage.
- `src/screens/*` — individual screen components for chat, next-question, and settings.

