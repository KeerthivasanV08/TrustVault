import { Link, useRouterState } from "@tanstack/react-router";
import {
  Activity, AlertTriangle, BarChart3, FileText, Network, ScanSearch,
  Settings, ShieldAlert, Users, Briefcase, UserCog, Radar,
} from "lucide-react";
import { useStore } from "@/store/realtime";

const NAV = [
  { to: "/", label: "Command Center", icon: Radar, exact: true },
  { to: "/transaction-flow", label: "Transaction Monitor", icon: Activity },
  { to: "/alerts", label: "Alert Center", icon: AlertTriangle, badge: "p1" },
  { to: "/graph", label: "Graph Explorer", icon: Network },
  { to: "/investigation", label: "Investigation", icon: ScanSearch },
  { to: "/officer-review", label: "Officer Review", icon: UserCog },
  { to: "/cases", label: "Cases", icon: Briefcase },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/accounts", label: "Account 360", icon: Users },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const path = useRouterState({ select: (s) => s.location.pathname });
  const p1 = useStore((s) => s.metrics.p1);

  return (
    <aside className="w-60 shrink-0 border-r border-sidebar-border bg-sidebar text-sidebar-foreground flex flex-col">
      <div className="h-14 px-4 flex items-center gap-2 border-b border-sidebar-border">
        <div className="relative">
          <ShieldAlert className="h-6 w-6 text-primary" />
          <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-success pulse-dot text-success" />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold tracking-wide">TrustVault</div>
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">AML Console</div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-2 px-2 scrollbar-thin">
        <div className="px-2 pt-2 pb-1 text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Operations</div>
        {NAV.map((item) => {
          const active = item.exact ? path === item.to : path === item.to || path.startsWith(item.to + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`relative flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] mb-0.5 transition-colors ${
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
              }`}
            >
              {active && <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 bg-primary rounded-r" />}
              <Icon className="h-4 w-4" />
              <span className="flex-1">{item.label}</span>
              {item.badge === "p1" && p1 > 0 && (
                <span className="text-[10px] mono px-1.5 py-0.5 rounded bg-critical/20 text-critical border border-critical/40">
                  {p1}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-sidebar-border p-3 text-[11px]">
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="mono">v4.12.3-prod</span>
          <span className="flex items-center gap-1">
            <BarChart3 className="h-3 w-3" />
            <span className="mono">99.97%</span>
          </span>
        </div>
      </div>
    </aside>
  );
}
