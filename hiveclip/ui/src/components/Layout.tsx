import { Outlet, Link, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { BoardRail } from "./BoardRail";
import { LayoutDashboard, Settings, LogOut } from "lucide-react";
import { Button } from "./ui/button";
import { Separator } from "./ui/separator";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./ui/tooltip";

export function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex h-screen bg-background text-foreground">
        {/* Icon rail */}
        <div className="flex w-12 flex-col items-center border-r border-border bg-sidebar py-3 gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Link to="/">
                <Button variant={location.pathname === "/" ? "secondary" : "ghost"} size="icon" className="h-8 w-8">
                  <LayoutDashboard className="h-4 w-4" />
                </Button>
              </Link>
            </TooltipTrigger>
            <TooltipContent side="right">Boards</TooltipContent>
          </Tooltip>

          <Separator className="my-1 w-6" />

          <BoardRail />

          <div className="mt-auto flex flex-col gap-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Link to="/settings">
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Settings className="h-4 w-4" />
                  </Button>
                </Link>
              </TooltipTrigger>
              <TooltipContent side="right">Settings</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={logout}>
                  <LogOut className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">Logout ({user?.email})</TooltipContent>
            </Tooltip>
          </div>
        </div>

        {/* Main content */}
        <div className="flex-1 overflow-auto">
          <Outlet />
        </div>
      </div>
    </TooltipProvider>
  );
}
