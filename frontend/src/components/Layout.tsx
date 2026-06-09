import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";

interface LayoutProps {
  title: string;
  back?: string | (() => void);
  showNav?: boolean;
  sessionId?: string | null;
  rightSlot?: ReactNode;
  children: ReactNode;
}

export function Layout({
  title,
  back,
  showNav = true,
  sessionId,
  rightSlot,
  children,
}: LayoutProps) {
  const navigate = useNavigate();
  const onBack = () => {
    if (typeof back === "function") back();
    else if (typeof back === "string") navigate(back);
    else navigate(-1);
  };
  return (
    <div className="flex flex-col min-h-[100dvh] bg-background">
      <header className="w-full top-0 sticky shadow-sm bg-surface z-40 flex items-center justify-between px-gutter py-stack-sm h-16">
        {back !== undefined ? (
          <button
            aria-label="Go back"
            onClick={onBack}
            className="w-10 h-10 flex items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container-low transition-colors active:scale-95 duration-200"
          >
            <span className="material-symbols-outlined">arrow_back</span>
          </button>
        ) : (
          <div className="flex items-center gap-2">
            <span
              className="material-symbols-outlined filled text-primary"
              aria-hidden
            >
              restaurant_menu
            </span>
            <h1 className="font-headline-md text-headline-md-mobile text-primary font-bold tracking-tight">
              PetPooja
            </h1>
          </div>
        )}
        <h1 className="font-headline-md text-headline-md-mobile text-on-surface font-semibold truncate max-w-[60%]">
          {title}
        </h1>
        <div className="w-10 h-10 flex items-center justify-center">
          {rightSlot}
        </div>
      </header>

      <main className="flex-1 w-full max-w-3xl mx-auto px-gutter pb-32 md:px-container-margin-desktop">
        {children}
      </main>

      {showNav && sessionId && <BottomNav sessionId={sessionId} />}
    </div>
  );
}

function BottomNav({ sessionId }: { sessionId: string }) {
  const tabs = [
    { to: `/sessions/${sessionId}/menu`, icon: "restaurant_menu", label: "Menu" },
    {
      to: `/sessions/${sessionId}/cart`,
      icon: "shopping_cart_checkout",
      label: "Group Cart",
    },
    {
      to: `/sessions/${sessionId}/bill`,
      icon: "receipt_long",
      label: "Bill",
    },
  ];
  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-50 rounded-t-xl border-t border-outline-variant/10 bg-surface-container-lowest shadow-[0_-4px_20px_-10px_rgba(0,0,0,0.1)] pb-safe">
      <div className="flex justify-around items-center h-16 px-4">
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              isActive
                ? "flex flex-col items-center justify-center bg-primary-container text-on-primary-container rounded-full px-5 py-1 active:scale-90 transition-transform"
                : "flex flex-col items-center justify-center text-on-surface-variant hover:text-primary active:scale-90 transition-transform px-5 py-1"
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={`material-symbols-outlined mb-1 ${
                    isActive ? "filled" : ""
                  }`}
                  aria-hidden
                >
                  {tab.icon}
                </span>
                <span className="font-label-sm text-[10px] leading-none font-medium">
                  {tab.label}
                </span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
