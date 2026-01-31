interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "error" | "outline";
  className?: string;
}

const variantClasses: Record<NonNullable<BadgeProps["variant"]>, string> = {
  default:
    "bg-neutral-800 text-neutral-300 border-neutral-700",
  success:
    "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  warning:
    "bg-amber-500/10 text-amber-400 border-amber-500/20",
  error:
    "bg-red-500/10 text-red-400 border-red-500/20",
  outline:
    "bg-transparent text-neutral-400 border-neutral-700",
};

export function Badge({
  children,
  variant = "default",
  className = "",
}: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-medium leading-none ${variantClasses[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
