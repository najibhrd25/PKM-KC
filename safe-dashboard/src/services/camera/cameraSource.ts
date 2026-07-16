export type CameraSourceKind = 'placeholder' | 'raspberry-pi-stream' | 'device-camera';

export interface CameraSource {
  kind: CameraSourceKind;
  label: string;
  streamUrl?: string;
}

export const developmentCameraSource: CameraSource = {
  kind: 'placeholder',
  label: 'Development placeholder',
};

export function createRaspberryPiCameraSource(streamUrl: string): CameraSource {
  return {
    kind: 'raspberry-pi-stream',
    label: 'Raspberry Pi stream',
    streamUrl,
  };
}

