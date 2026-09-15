import { useCallback, useEffect, useState } from "react";
import Cropper from "react-easy-crop";
import { X, ZoomIn, ZoomOut, Check } from "lucide-react";

/**
 * 1:1 photo cropper modal.
 *
 * Props:
 *   - file: File selected by the user (image/*).
 *   - onCancel(): closes the modal without uploading.
 *   - onConfirm(blob): called with a cropped/compressed JPEG Blob (512×512, q=0.85).
 *
 * The cropped output is capped at 512px on the long side and encoded as JPEG at
 * quality 0.85. This keeps profile photos ~40–80KB — small enough to load
 * instantly on mobile and uniform in aspect ratio across the whole site.
 */
const OUTPUT_SIZE = 512;
const OUTPUT_QUALITY = 0.85;

async function cropImageToBlob(imageSrc, cropPixels) {
  const image = await new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.crossOrigin = "anonymous";
    img.src = imageSrc;
  });

  const canvas = document.createElement("canvas");
  canvas.width = OUTPUT_SIZE;
  canvas.height = OUTPUT_SIZE;
  const ctx = canvas.getContext("2d");
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(
    image,
    cropPixels.x, cropPixels.y, cropPixels.width, cropPixels.height,
    0, 0, OUTPUT_SIZE, OUTPUT_SIZE,
  );

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Canvas encoding failed"))),
      "image/jpeg",
      OUTPUT_QUALITY,
    );
  });
}

export default function PhotoCropperModal({ file, onCancel, onConfirm }) {
  const [imageSrc, setImageSrc] = useState(null);
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState(null);
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    if (!file) { setImageSrc(null); return; }
    const reader = new FileReader();
    reader.onload = () => setImageSrc(reader.result);
    reader.readAsDataURL(file);
  }, [file]);

  const onCropComplete = useCallback((_areaPercent, areaPixels) => {
    setCroppedAreaPixels(areaPixels);
  }, []);

  const handleConfirm = async () => {
    if (!imageSrc || !croppedAreaPixels) return;
    setProcessing(true);
    try {
      const blob = await cropImageToBlob(imageSrc, croppedAreaPixels);
      onConfirm(blob);
    } catch (e) {
      console.error("[Cropper] failed:", e);
      alert("Errore nell'elaborazione dell'immagine.");
      setProcessing(false);
    }
  };

  if (!file) return null;

  return (
    <div data-testid="photo-cropper-modal" className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#0A0A0A]/10">
          <h3 className="font-semibold text-[#0A0A0A] font-[Outfit]">Ritaglia la foto profilo</h3>
          <button
            type="button"
            data-testid="cropper-close"
            onClick={onCancel}
            className="p-1.5 rounded-lg hover:bg-[#0A0A0A]/5 text-[#0A0A0A]/55"
            disabled={processing}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="relative w-full aspect-square bg-[#0A0A0A]">
          {imageSrc && (
            <Cropper
              image={imageSrc}
              crop={crop}
              zoom={zoom}
              aspect={1}
              cropShape="round"
              showGrid={false}
              onCropChange={setCrop}
              onZoomChange={setZoom}
              onCropComplete={onCropComplete}
            />
          )}
        </div>

        <div className="px-5 py-4 space-y-4">
          <div className="flex items-center gap-3">
            <ZoomOut className="w-4 h-4 text-[#0A0A0A]/55 flex-shrink-0" />
            <input
              data-testid="cropper-zoom"
              type="range"
              min={1}
              max={3}
              step={0.05}
              value={zoom}
              onChange={(e) => setZoom(Number(e.target.value))}
              className="flex-1 accent-[#F58A1F]"
              disabled={processing}
            />
            <ZoomIn className="w-4 h-4 text-[#0A0A0A]/55 flex-shrink-0" />
          </div>
          <p className="text-xs text-[#0A0A0A]/55 text-center">
            Trascina per spostare · usa lo slider per ingrandire
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              data-testid="cropper-cancel"
              onClick={onCancel}
              disabled={processing}
              className="flex-1 px-4 py-2.5 rounded-xl border border-[#0A0A0A]/15 text-sm font-medium text-[#0A0A0A] hover:bg-[#0A0A0A]/5 transition-colors disabled:opacity-50"
            >
              Annulla
            </button>
            <button
              type="button"
              data-testid="cropper-confirm"
              onClick={handleConfirm}
              disabled={processing || !croppedAreaPixels}
              className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-[#0A0A0A] text-white text-sm font-semibold hover:bg-[#0A0A0A]/85 transition-colors disabled:opacity-50"
            >
              <Check className="w-4 h-4" /> {processing ? "Elaboro..." : "Conferma"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
