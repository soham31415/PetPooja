import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";

interface Toast {
  id: number;
  icon: string;
  message: string;
}

interface ToastContextValue {
  showToast: (message: string, icon?: string) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

let nextId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((message: string, icon = "waving_hand") => {
    const id = ++nextId;
    setToasts((t) => [...t, { id, icon, message }]);
    setTimeout(() => {
      setToasts((t) => t.filter((x) => x.id !== id));
    }, 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-24 md:bottom-8 left-1/2 -translate-x-1/2 z-[70] pointer-events-none flex flex-col items-center gap-2 w-max max-w-[90vw]">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="bg-inverse-surface text-inverse-on-surface px-4 py-3 rounded-full shadow-lg flex items-center gap-3 animate-slide-up-fade"
          >
            <span
              className="material-symbols-outlined filled text-primary-fixed-dim"
              aria-hidden
            >
              {t.icon}
            </span>
            <span className="font-body-md text-body-md font-medium">
              {t.message}
            </span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be inside <ToastProvider>");
  return ctx;
}
