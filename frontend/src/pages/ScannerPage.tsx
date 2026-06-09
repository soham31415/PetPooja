import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

export function ScannerPage() {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const scannerRef = useRef<{ stop: () => Promise<void> } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [manualOpen, setManualOpen] = useState(false);
  const [manual, setManual] = useState("");

  useEffect(() => {
    let stopped = false;

    (async () => {
      try {
        const { Html5Qrcode } = await import("html5-qrcode");
        const elementId = "qr-reader";
        if (!containerRef.current) return;
        // ensure the target element exists with the expected id
        containerRef.current.id = elementId;

        const scanner = new Html5Qrcode(elementId, { verbose: false });
        scannerRef.current = scanner;

        await scanner.start(
          { facingMode: "environment" },
          { fps: 10, qrbox: { width: 240, height: 240 } },
          (decoded) => {
            if (stopped) return;
            stopped = true;
            const token = extractToken(decoded);
            scanner
              .stop()
              .catch(() => undefined)
              .finally(() => navigate(`/scan/${encodeURIComponent(token)}`));
          },
          () => undefined
        );
      } catch (err) {
        const msg =
          (err as { message?: string })?.message ||
          "Camera not available. Use a code manually.";
        setError(msg);
        setManualOpen(true);
      }
    })();

    return () => {
      stopped = true;
      scannerRef.current?.stop().catch(() => undefined);
    };
  }, [navigate]);

  const submitManual = (e: React.FormEvent) => {
    e.preventDefault();
    const token = extractToken(manual.trim());
    if (token) navigate(`/scan/${encodeURIComponent(token)}`);
  };

  return (
    <div className="relative flex flex-col h-[100dvh] bg-inverse-surface text-inverse-on-surface overflow-hidden">
      <div
        ref={containerRef}
        className="absolute inset-0 opacity-70 [&_video]:!object-cover [&_video]:!w-full [&_video]:!h-full"
      />
      <div className="absolute inset-0 bg-inverse-surface/30" />

      <header className="relative z-20 flex items-center justify-between px-container-margin-mobile pt-12 w-full">
        <button
          onClick={() => navigate("/")}
          className="w-12 h-12 rounded-full glass-dark flex items-center justify-center text-inverse-on-surface border border-outline-variant/20"
          aria-label="Close"
        >
          <span className="material-symbols-outlined">close</span>
        </button>
        <div className="px-4 py-2 rounded-full glass-dark border border-outline-variant/20">
          <span className="font-label-sm text-label-sm">Scan Table Code</span>
        </div>
        <div className="w-12 h-12" />
      </header>

      <div className="relative z-10 flex-1 flex items-center justify-center px-container-margin-mobile">
        <div className="relative w-64 h-64">
          <div className="absolute inset-0 border-2 rounded-3xl animate-scan-pulse overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-8 animate-scan-line bg-gradient-to-b from-transparent via-primary/80 to-transparent" />
          </div>
          <div className="absolute top-0 left-0 w-8 h-8 border-t-4 border-l-4 border-primary rounded-tl-3xl" />
          <div className="absolute top-0 right-0 w-8 h-8 border-t-4 border-r-4 border-primary rounded-tr-3xl" />
          <div className="absolute bottom-0 left-0 w-8 h-8 border-b-4 border-l-4 border-primary rounded-bl-3xl" />
          <div className="absolute bottom-0 right-0 w-8 h-8 border-b-4 border-r-4 border-primary rounded-br-3xl" />
        </div>
      </div>

      <div className="relative z-20 px-container-margin-mobile pb-safe mb-8">
        <div className="glass-dark rounded-2xl p-6 border border-outline-variant/20 text-center">
          {error ? (
            <p className="font-body-md text-body-md">{error}</p>
          ) : (
            <p className="font-body-md text-body-md">
              Align the QR code on your table within the frame.
            </p>
          )}
          <button
            onClick={() => setManualOpen(true)}
            className="font-label-sm text-label-sm text-inverse-primary mt-2 underline underline-offset-4"
          >
            Enter code manually instead
          </button>
        </div>
      </div>

      {manualOpen && (
        <div className="absolute inset-0 z-30 bg-background/95 backdrop-blur-md flex items-center justify-center px-container-margin-mobile">
          <form
            onSubmit={submitManual}
            className="w-full max-w-md bg-surface-container-lowest rounded-2xl p-6 shadow-lg flex flex-col gap-4"
          >
            <h2 className="font-headline-md text-headline-md-mobile text-on-surface">
              Enter table code
            </h2>
            <p className="font-body-md text-body-md text-on-surface-variant">
              You&rsquo;ll find this on the QR card on your table, or paste a
              link.
            </p>
            <input
              autoFocus
              value={manual}
              onChange={(e) => setManual(e.target.value)}
              placeholder="e.g. JVz3FhTbUcLbmVmkoxzSHg"
              className="h-12 px-4 rounded-xl border border-outline/40 bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none font-body-md text-body-md"
            />
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setManualOpen(false)}
                className="flex-1 h-12 rounded-full border border-outline text-on-surface font-label-md text-label-md"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!manual.trim()}
                className="flex-1 h-12 rounded-full bg-primary text-on-primary font-label-md text-label-md disabled:opacity-50"
              >
                Continue
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

/** Pull a qr_token out of either a raw token or a deep link URL. */
function extractToken(input: string): string {
  const trimmed = input.trim();
  try {
    const u = new URL(trimmed);
    const m = u.pathname.match(/\/(?:scan|tables)\/([^/?#]+)/);
    if (m) return decodeURIComponent(m[1]!);
  } catch {
    // not a URL — treat as raw token
  }
  return trimmed;
}
