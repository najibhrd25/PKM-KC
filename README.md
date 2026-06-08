# S.A.F.E. Mobile

React Native mobile app for S.A.F.E. built with Expo SDK 54.

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

For Expo Go on iPhone, run `pnpm dev` and scan the QR code from Expo Go. SDK 54 is used so the project can open from the App Store version of Expo Go.

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
