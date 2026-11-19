import { useEffect, useRef, useState } from "react";
import { Alert } from "./AuthKit";
import { decodeImageData } from "../qr/decodeFrame";
import "../styles/qr.css";

function explain(e: unknown): string {
  const name = e instanceof Error ? e.name : "";
  switch (name) {
    case "NotAllowedError": case "SecurityError": case "PermissionDeniedError":
      return "Camera permission was denied. Click the camera icon in the address bar, allow access, then try again.";
    case "NotFoundError": case "DevicesNotFoundError": case "OverconstrainedError":
      return "No camera was found on this device.";
    case "NotReadableError": case "TrackStartError": case "AbortError":
      return "The camera could not be started. It may be in use by another app or browser tab. Close it and try again.";
    default:
      return "The camera could not be opened. You can upload a QR image instead.";
  }
}

/** Live camera QR scanner. Asks for camera permission when it mounts (the parent mounts it only after a click),
 *  decodes frames in the browser, and always stops the camera when scanning ends or the component unmounts. */
export default function QrCamera({ onDecoded, onClose }: { onDecoded: (text: string) => void; onClose: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const callback = useRef(onDecoded);
  callback.current = onDecoded;
  const [state, setState] = useState<"starting" | "live" | "error">("starting");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let stream: MediaStream | undefined;
    let raf = 0;
    let stopped = false;
    let last = 0;
    const stop = () => {
      stopped = true;
      cancelAnimationFrame(raf);
      stream?.getTracks().forEach((t) => t.stop());
      if (videoRef.current) videoRef.current.srcObject = null;
    };
    const fail = (text: string) => { stop(); setMessage(text); setState("error"); };

    (async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        fail(window.isSecureContext ? "This browser does not provide camera access to web pages." : "Camera access needs a secure page (https or localhost).");
        return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false,
        });
        if (stopped) { stream.getTracks().forEach((t) => t.stop()); return; }
        const video = videoRef.current;
        if (!video) { stop(); return; }
        video.srcObject = stream;
        await video.play();
        setState("live");
        const tick = (now: number) => {
          if (stopped) return;
          raf = requestAnimationFrame(tick);
          if (now - last < 120 || video.readyState < 2 || !video.videoWidth) return;
          last = now;
          const scale = Math.min(1, 800 / video.videoWidth);
          const w = Math.round(video.videoWidth * scale);
          const h = Math.round(video.videoHeight * scale);
          const canvas = canvasRef.current;
          const ctx = canvas?.getContext("2d", { willReadFrequently: true });
          if (!canvas || !ctx) return;
          canvas.width = w;
          canvas.height = h;
          ctx.drawImage(video, 0, 0, w, h);
          const text = decodeImageData(ctx.getImageData(0, 0, w, h).data, w, h);
          if (text) { stop(); callback.current(text); }
        };
        raf = requestAnimationFrame(tick);
      } catch (e) {
        if (!stopped) fail(explain(e)); // a rejection caused by our own cleanup is not an error
      }
    })();
    return stop;
  }, []);

  return (
    <div className="camera" role="region" aria-label="Camera scanner">
      <video ref={videoRef} className="preview camvideo" muted playsInline aria-label="Live camera preview" style={{ display: state === "error" ? "none" : undefined }} />
      <canvas ref={canvasRef} hidden />
      {state === "starting" && <p className="sub">Starting the camera. Allow access if your browser asks.</p>}
      {state === "live" && <p className="sub">Point the camera at a QR code. It scans automatically and nothing is opened.</p>}
      {state === "error" && <Alert>{message}</Alert>}
      <button type="button" className="btn" onClick={onClose}>Stop camera</button>
    </div>
  );
}
