import clsx from "clsx";

interface StatsCardProps {
  label: string;
  value: string | number;
  icon: string;
  color?: "blue" | "green" | "yellow" | "red";
  subtitle?: string;
}

const colorMap: Record<NonNullable<StatsCardProps["color"]>, string> = {
  blue:   "bg-blue-500/10 border-blue-500/20 text-blue-400",
  green:  "bg-green-500/10 border-green-500/20 text-green-400",
  yellow: "bg-yellow-500/10 border-yellow-500/20 text-yellow-400",
  red:    "bg-red-500/10 border-red-500/20 text-red-400",
};

export default function StatsCard({ label, value, icon, color = "blue", subtitle }: StatsCardProps) {
  return (
    <div className={clsx(
      "rounded-xl border p-4 flex items-center gap-4",
      colorMap[color],
    )}>
      <span className="text-3xl">{icon}</span>
      <div>
        <p className="text-2xl font-bold text-white">{value}</p>
        <p className="text-sm font-medium opacity-80">{label}</p>
        {subtitle && <p className="text-xs opacity-60 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  );
}
