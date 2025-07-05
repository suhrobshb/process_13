import { Link, useLocation } from "wouter";
import { cn } from "@/lib/utils";
import {
    LayoutDashboard,
    Video,
    GitFork,
    PlayCircle,
    BrainCircuit,
    PlugZap,
    Settings,
    Icon as LucideIcon,
} from "lucide-react";

// Define the type for a navigation item, including an icon mapping
export interface NavItem {
    title: string;
    href: string;
    icon: keyof typeof icons;
}

// Map icon names to the actual Lucide React components for easy lookup
const icons = {
    dashboard: LayoutDashboard,
    recording: Video,
    workflows: GitFork,
    executions: PlayCircle,
    learning: BrainCircuit,
    integrations: PlugZap,
    settings: Settings,
};

// The definitive list of navigation items for the AI Engine sidebar
export const navItems: NavItem[] = [
    { title: "Dashboard", href: "/", icon: "dashboard" },
    { title: "Recording", href: "/recording", icon: "recording" },
    { title: "Workflows", href: "/workflows", icon: "workflows" },
    { title: "Executions", href: "/executions", icon: "executions" },
    { title: "AI Learning Center", href: "/learning", icon: "learning" },
    { title: "Integrations", href: "/integrations", icon: "integrations" },
    { title: "Settings", href: "/settings", icon: "settings" },
];

export function Sidebar() {
    // useLocation hook from wouter to get the current path
    const [location] = useLocation();

    return (
        <nav className="grid items-start gap-2">
            {navItems.map((item, index) => {
                // Dynamically select the icon component based on the item's icon key
                const Icon = icons[item.icon];
                return (
                    // Ensure item has a link before rendering
                    item.href && (
                        <Link
                            key={index}
                            href={item.href}
                            className={cn(
                                "group flex items-center rounded-md px-3 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground",
                                // Apply 'bg-accent' class if the current location matches the item's href
                                location === item.href ? "bg-accent" : "transparent"
                            )}
                        >
                            <Icon className="mr-2 h-4 w-4" />
                            <span>{item.title}</span>
                        </Link>
                    )
                );
            })}
        </nav>
    );
}
