# S.A.F.E. Mobile

React Native mobile app for S.A.F.E. built with Expo.

## Run Locally

Install dependencies:

```bash
pnpm install
```

Start the iOS Simulator:

```bash
pnpm ios
```

Or start Expo and press `i`:

```bash
pnpm dev
```

## Structure

```txt
assets/
  audio/
  icons/
  images/
src/
  app/
  core/
  features/
  services/
  shared/
  store/
```

## Camera Plan

The mission control screen currently renders a native placeholder camera panel.
The app is structured so the camera source can later be swapped to a Raspberry Pi stream service.

For iOS Simulator, physical camera hardware is not available. Real camera testing should use a physical iPhone or a Raspberry Pi stream endpoint.

