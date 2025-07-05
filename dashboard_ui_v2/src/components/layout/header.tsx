import { ModeToggle } from "@/components/layout/mode-toggle";
import { UserNav } from "@/components/layout/user-nav";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Menu, Bot } from "lucide-react";
import { NavItem } from "./sidebar";

export const navItems: NavItem[] = [
    { title: "Dashboard", href: "/", icon: "dashboard" },
    { title: "Recording", href: "/recording", icon: "recording" },
    { title: "Workflows", href: "/workflows", icon: "workflows" },
    { title: "Executions", href: "/executions", icon: "executions" },
    { title: "AI Learning Center", href: "/learning", icon: "learning" },
    { title: "Integrations", href: "/integrations", icon: "integrations" },
    { title: "Settings", href: "/settings", icon: "settings" },
];

export function Header() {
    return (
        <header className="sticky top-0 z-10 w-full bg-background/95 shadow-sm backdrop-blur-sm dark:bg-background/80">
            <div className="container flex h-14 items-center">
                <div className="mr-4 hidden md:flex">
                    <a href="/" className="mr-6 flex items-center space-x-2">
                        <Bot className="h-6 w-6" />
                        <span className="hidden font-bold sm:inline-block">
                            AI Engine
                        </span>
                    </a>
                </div>

                {/* Mobile Menu */}
                <Sheet>
                    <SheetTrigger asChild>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="mr-2 md:hidden"
                        >
                            <Menu className="h-5 w-5" />
                            <span className="sr-only">Toggle Menu</span>
                        </Button>
                    </SheetTrigger>
                    <SheetContent side="left" className="pr-0">
                        <a href="/" className="flex items-center space-x-2 mb-4">
                            <Bot className="h-6 w-6" />
                            <span className="font-bold">AI Engine</span>
                        </a>
                        <div className="flex flex-col space-y-2">
                            {/* Mobile nav items can be mapped here if needed */}
                        </div>
                    </SheetContent>
                </Sheet>
                
                <div className="flex flex-1 items-center justify-end space-x-2">
                    <ModeToggle />
                    <UserNav />
                </div>
            </div>
        </header>
    );
}
