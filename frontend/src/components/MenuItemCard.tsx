import type { MenuItem } from "../api";

interface MenuItemCardProps {
  item: MenuItem;
  variant?: "featured" | "row";
  matchScore?: number;
  onAdd?: (item: MenuItem) => void;
  busy?: boolean;
}

function fmtPrice(p: number): string {
  return `$${p.toFixed(p % 1 === 0 ? 0 : 2)}`;
}

function TagPill({ tag }: { tag: string }) {
  const lower = tag.toLowerCase();
  const tone =
    lower.includes("veg") || lower.includes("vegan") || lower.includes("gf")
      ? "bg-tertiary-fixed text-on-tertiary-fixed"
      : "bg-surface-container-high text-on-surface-variant";
  return (
    <span
      className={`px-2 py-1 rounded-md font-label-sm text-[10px] uppercase tracking-wide ${tone}`}
    >
      {tag}
    </span>
  );
}

export function MenuItemCard({
  item,
  variant = "row",
  matchScore,
  onAdd,
  busy,
}: MenuItemCardProps) {
  if (variant === "featured") {
    return (
      <article className="bg-surface-container-lowest rounded-2xl shadow-sm border border-surface-variant/50 overflow-hidden group">
        <div className="relative h-48 md:h-64 w-full bg-surface-variant flex items-center justify-center">
          <span
            className="material-symbols-outlined text-on-surface-variant text-[64px] opacity-40"
            aria-hidden
          >
            restaurant
          </span>
          {matchScore !== undefined && (
            <div className="absolute top-4 left-4">
              <span className="bg-surface/90 backdrop-blur-sm px-3 py-1 rounded-full font-label-sm text-label-sm text-primary flex items-center gap-1 shadow-sm">
                <span
                  className="material-symbols-outlined text-[16px]"
                  aria-hidden
                >
                  thumb_up
                </span>
                {Math.round(matchScore * 100)}% Match
              </span>
            </div>
          )}
        </div>
        <div className="p-stack-md">
          <div className="flex justify-between items-start mb-2">
            <h3 className="font-headline-md text-[20px] leading-[28px] font-semibold text-on-surface">
              {item.name}
            </h3>
            <span className="font-headline-md text-[20px] font-semibold text-on-surface">
              {fmtPrice(item.price)}
            </span>
          </div>
          <p className="font-body-md text-body-md text-on-surface-variant mb-4 line-clamp-2">
            {item.description}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {item.tags.slice(0, 3).map((t) => (
              <TagPill key={t} tag={t} />
            ))}
            <button
              disabled={busy}
              onClick={() => onAdd?.(item)}
              className="ml-auto bg-primary text-on-primary px-4 py-2 rounded-full font-label-md text-label-md hover:bg-surface-tint transition-colors active:scale-95 disabled:opacity-50"
            >
              Add to cart
            </button>
          </div>
        </div>
      </article>
    );
  }

  return (
    <article className="flex gap-4 p-4 rounded-xl hover:bg-surface-container-lowest transition-colors group border border-transparent hover:border-surface-variant/30 hover:shadow-sm">
      <div className="w-24 h-24 md:w-32 md:h-32 rounded-2xl overflow-hidden flex-shrink-0 shadow-sm bg-surface-variant flex items-center justify-center">
        <span
          className="material-symbols-outlined text-on-surface-variant text-[40px] opacity-40"
          aria-hidden
        >
          restaurant
        </span>
      </div>
      <div className="flex-1 flex flex-col justify-center min-w-0">
        <div className="flex justify-between items-start gap-2">
          <h3 className="font-headline-md text-[18px] md:text-[20px] font-semibold text-on-surface truncate">
            {item.name}
          </h3>
          <span className="font-label-md text-label-md font-semibold text-on-surface whitespace-nowrap">
            {fmtPrice(item.price)}
          </span>
        </div>
        <p className="font-body-md text-[14px] leading-[20px] text-on-surface-variant mt-1 mb-2 line-clamp-2">
          {item.description || "—"}
        </p>
        <div className="flex items-center gap-2 mt-auto">
          {item.tags.slice(0, 2).map((t) => (
            <TagPill key={t} tag={t} />
          ))}
          <button
            disabled={busy}
            onClick={() => onAdd?.(item)}
            className="ml-auto bg-surface-container text-on-surface px-4 py-1.5 rounded-full font-label-sm text-label-sm border border-outline/20 hover:border-primary hover:text-primary transition-colors disabled:opacity-50"
          >
            Add
          </button>
        </div>
      </div>
    </article>
  );
}
