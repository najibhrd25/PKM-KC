import type { CameraSource } from '@/lib/cameraSource';
import { Card } from '@/components/ui/Card';

interface VideoPanelProps {
  isOff: boolean;
  cameraVisible: boolean;
  source: CameraSource;
}

export function VideoPanel({ isOff }: VideoPanelProps) {
  return (
    <Card
      className={`relative w-full aspect-[16/10.5] max-h-[235px] overflow-hidden bg-black ${
        isOff ? 'opacity-[0.45]' : ''
      }`}
    >
      <div className="absolute inset-0 overflow-hidden">
        {/*
          Untuk mengganti gambar/video kamera:
          1. Letakkan file Anda di folder: public/ (contoh: public/live-camera.png atau public/Recordddddd.mp4)
          2. Ubah atribut 'src' di bawah ini:
             - Foto:  <img src="/live-camera.png" alt="Live Camera Feed" className="h-full w-full object-cover object-center" />
             - Video: <video src="/Recordddddd.mp4" autoPlay loop muted playsInline className="h-full w-full object-cover object-center" />
        */}
        <img
          src="/live-camera.png"
          alt="Live Camera Feed"
          className="h-full w-full object-cover object-center"
        />
      </div>
    </Card>
  );
}

