# S.A.F.E. Mobile Architecture

Branch `react-native-safe` is a full React Native / Expo branch focused on mobile.

## App Target

- Expo SDK 56
- Expo Router
- React Native 0.85
- iOS Simulator first
- `pnpm` package manager

## Folder Structure

```txt
assets/
  audio/       Startup, alert, and hardware sounds
  icons/       Future custom icons
  images/      Expo icon, splash, and image assets
src/
  app/         Expo Router routes and providers
  core/        Reusable system logic and types
  features/    Feature screens and components
  services/    Camera, Raspberry Pi API, and integrations
  shared/      Theme and reusable native UI
  store/       App state hooks
```

## Camera Direction

The current camera panel is a native placeholder. The UI talks through `src/services/camera`, so the source can later become:

- Raspberry Pi stream
- physical iPhone camera
- local development placeholder

For S.A.F.E., the Raspberry Pi stream is the expected production source. iOS Simulator is enough for UI work, but real camera/hardware validation should happen on a physical iPhone or with the Pi stream URL.

## Web Code Policy

This branch intentionally removes Next.js and web dashboard code from the mobile app surface. The old web implementation remains available in prior branches for reference.

