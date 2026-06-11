import type { OrderStatus } from "../api";

const COPY: Record<
  OrderStatus,
  { label: string; icon: string; classes: string }
> = {
  pending: {
    label: "Pending",
    icon: "schedule",
    classes: "bg-secondary-container text-on-secondary-container",
  },
  confirmed: {
    label: "Confirmed",
    icon: "skillet",
    classes: "bg-[#fdf5e6] text-[#5c3a00] border border-[#f5d0a9]",
  },
  paid: {
    label: "Paid",
    icon: "check_circle",
    classes: "bg-tertiary-fixed text-on-tertiary-fixed",
  },
};

export function OrderStatusPill({
  status,
  size = "sm",
}: {
  status: OrderStatus;
  size?: "sm" | "md";
}) {
  const { label, icon, classes } = COPY[status];
  const sizing =
    size === "md"
      ? "px-4 py-2 font-label-md text-label-md"
      : "px-3 py-1 font-label-sm text-label-sm";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full ${sizing} ${classes}`}
    >
      <span className="material-symbols-outlined text-[16px]" aria-hidden>
        {icon}
      </span>
      {label}
    </span>
  );
}
