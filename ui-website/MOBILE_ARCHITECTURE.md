# S.A.F.E. Mobile Architecture

Branch `react-native-safe` is a full React Native / Expo branch focused on mobile.

## App Target

- Expo SDK 54
- Expo Router
- NativeWind 4
- React Native 0.81
- iOS Simulator first
- Expo Go on iPhone supported for quick previews
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
  shared/      Reusable native UI
  store/       App state hooks
```

## Camera Direction

The current camera panel is a native placeholder. The UI talks through `src/services/camera`, so the source can later become:

- Raspberry Pi stream
- physical iPhone camera
- local development placeholder

For S.A.F.E., the Raspberry Pi stream is the expected production source. iOS Simulator is enough for UI work, but real camera/hardware validation should happen on a physical iPhone or with the Pi stream URL.

## Styling Direction

- Use NativeWind `className` for static layout and visual styling.
- Use inline `style` only for values calculated at runtime.
- Keep shared design tokens in `tailwind.config.js`.
- Do not add component-level CSS selectors or duplicate NativeWind utilities in `StyleSheet`.

## Web Code Policy

This branch intentionally removes Next.js and web dashboard code from the mobile app surface. The old web implementation remains available in prior branches for reference.
