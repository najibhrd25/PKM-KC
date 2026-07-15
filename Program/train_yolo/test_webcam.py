from ultralytics import YOLO

def main():
    print("Memuat Otak S.A.F.E. Versi Nano...")
    
    model = YOLO('train-4/weights/best.pt')
    
    print("Membuka kamera... Tekan 'q' pada keyboard untuk keluar.")
    
    # conf=0.5 artinya AI hanya mendeteksi jika yakin 50% ke atas
    model.predict(source=0, show=True, conf=0.5)

if __name__ == '__main__':
    main()