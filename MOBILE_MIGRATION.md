# Mobile App Migration Plan

Project ini sedang disiapkan agar logic S.A.F.E. bisa dipakai ulang saat pindah ke React Native.

## Branch Kerja

Refactor mobile dilakukan di branch:

```bash
mobile-app-refactor
```

Tujuannya agar `main` tetap aman selama struktur, dependency, dan UI mobile disiapkan.

Package manager project ini adalah `pnpm`. Gunakan command seperti:

```bash
pnpm lint
pnpm build
pnpm dev
```

## Strategi

1. Pertahankan dashboard Next.js tetap jalan sebagai web preview.
2. Pindahkan logic yang tidak bergantung browser ke `src/core`.
3. Biarkan komponen Next.js/Tailwind tetap di `src/components` dan `src/app`.
4. Saat React Native dibuat, screen native mengambil logic dari `src/core`, lalu UI ditulis ulang memakai komponen native.

## Struktur Saat Ini

```txt
src/
  app/                 Next.js App Router
  components/          UI web dashboard
  core/                Logic lintas platform
  platform/web/        Efek dan adapter khusus web
  store/               Zustand hook untuk app web saat ini
```

## Reusable Untuk React Native

- `src/core/system/types.ts`
- `src/core/system/constants.ts`
- state machine S.A.F.E.
- kontrak sensor dan mode operasi
- validasi password/manual mode

## Perlu Ditulis Ulang Di React Native

- layout dari `src/app/page.tsx`
- komponen Tailwind/HTML di `src/components`
- modal auth berbasis DOM
- joystick berbasis pointer event DOM
- audio web di `src/platform/web`

## Rekomendasi Stack Mobile

Gunakan Expo terlebih dahulu:

- `expo-router` untuk routing berbasis folder
- Zustand tetap bisa dipakai untuk state
- `expo-av` atau pengganti terbaru Expo untuk audio
- `react-native-gesture-handler` untuk joystick/manual control
- `react-native-svg` untuk HUD/reticle
- `nativewind` hanya jika ingin mempertahankan pola utility class mirip Tailwind

## Langkah Berikutnya

1. Scaffold app Expo di folder `apps/mobile`.
2. Buat screen native pertama: `MissionControlScreen`.
3. Ambil konstanta dan tipe dari `src/core/system`.
4. Buat adapter storage React Native untuk Zustand persist memakai AsyncStorage.
5. Ganti efek web seperti `Audio`, pointer event, dan Material Symbols dengan package native.

Saat pondasi di branch ini sudah selesai, lanjutkan migrasi native di branch baru agar perubahan React Native/Expo tidak tercampur dengan refactor persiapan.
