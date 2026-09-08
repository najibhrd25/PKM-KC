import type { CameraSource } from '@/lib/cameraSource';
import { Card } from '@/components/ui/Card';
// import { useEffect, useRef } from 'react'; // [AKTIFKAN JIKA PAKAI VIDEO]

interface VideoPanelProps {
  isOff: boolean;
  cameraVisible: boolean;
  source: CameraSource;
}

// [KODE OPSI VIDEO] - Aktifkan jika ingin memakai video looping:
// const START_TIME = 0.9888; // Detik mulai video (misal 55 detik atau awal)

export function VideoPanel({ isOff }: VideoPanelProps) {
  // [KODE OPSI VIDEO] - Hook kontrol video:
  // const videoRef = useRef<HTMLVideoElement>(null);
  // useEffect(() => {
  //   const video = videoRef.current;
  //   if (!video) return;
  //   const setInitialTime = () => {
  //     video.currentTime = START_TIME;
  //     video.play().catch(() => {});
  //   };
  //   const handleEnded = () => {
  //     video.currentTime = START_TIME;
  //     video.play().catch(() => {});
  //   };
  //   if (video.readyState >= 1) {
  //     setInitialTime();
  //   } else {
  //     video.addEventListener('loadedmetadata', setInitialTime, { once: true });
  //   }
  //   video.addEventListener('ended', handleEnded);
  //   return () => {
  //     video.removeEventListener('loadedmetadata', setInitialTime);
  //     video.removeEventListener('ended', handleEnded);
  //   };
  // }, []);

  return (
    <Card
      className={`relative w-full aspect-[16/10.5] max-h-[235px] overflow-hidden bg-black ${isOff ? 'opacity-[0.45]' : ''
        }`}
    >
      <div className="absolute inset-0 overflow-hidden">
        {/* ==================================================================== */}
        {/* 1. OPSI FOTO AKTIF (LIVE-CAMERA)                                      */}
        {/* ==================================================================== */}
        <img
          src="/live-camera.png"
          alt="Live Camera Feed"
          className="h-full w-full object-cover object-[center_50%] scale-[1.12] origin-center"
        />

        {/* ==================================================================== */}
        {/* 2. OPSI VIDEO (Aktifkan tag di bawah ini & matikan tag <img> di atas)  */}
        {/* ==================================================================== */}
        {/*
        <video
          ref={videoRef}
          src="/Recordddddd.mp4"
          autoPlay
          muted
          playsInline
          className="h-full w-full object-cover object-center scale-[1.18] origin-center"
        />
        */}
      </div>
    </Card>
  );
}


