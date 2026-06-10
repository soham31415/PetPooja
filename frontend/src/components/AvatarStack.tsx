import type { User } from "../api";

interface AvatarStackProps {
  users: User[];
  size?: "sm" | "md" | "lg";
  max?: number;
}

const SIZE: Record<NonNullable<AvatarStackProps["size"]>, string> = {
  sm: "w-8 h-8 text-[10px]",
  md: "w-10 h-10 text-xs",
  lg: "w-14 h-14 text-sm",
};

const PALETTE = [
  "bg-primary-fixed text-on-primary-fixed",
  "bg-tertiary-fixed text-on-tertiary-fixed",
  "bg-secondary-container text-on-secondary-container",
  "bg-primary-container text-on-primary-container",
];

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w[0]!.toUpperCase())
    .slice(0, 2)
    .join("");
}

export function AvatarStack({ users, size = "sm", max = 4 }: AvatarStackProps) {
  const shown = users.slice(0, max);
  const overflow = users.length - shown.length;
  return (
    <div className="flex -space-x-3">
      {shown.map((u, i) => (
        <div
          key={u.id}
          title={u.username}
          className={`${SIZE[size]} rounded-full border-2 border-surface flex items-center justify-center font-semibold ${PALETTE[i % PALETTE.length]}`}
        >
          {initials(u.username)}
        </div>
      ))}
      {overflow > 0 && (
        <div
          className={`${SIZE[size]} rounded-full border-2 border-surface bg-surface-container-high text-on-surface-variant flex items-center justify-center font-semibold`}
        >
          +{overflow}
        </div>
      )}
    </div>
  );
}

export function Avatar({
  user,
  size = "sm",
  paletteIndex = 0,
}: {
  user: { username: string };
  size?: AvatarStackProps["size"];
  paletteIndex?: number;
}) {
  return (
    <div
      className={`${SIZE[size!]} rounded-full flex items-center justify-center font-semibold ${PALETTE[paletteIndex % PALETTE.length]}`}
    >
      {initials(user.username)}
    </div>
  );
}
