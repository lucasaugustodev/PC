import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { fetchBoards } from "../api/boards";
import { Button } from "./ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "./ui/tooltip";
import { Skeleton } from "./ui/skeleton";

export function BoardRail() {
  const { boardId } = useParams();
  const { data: boards, isLoading } = useQuery({ queryKey: ["boards"], queryFn: fetchBoards });

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-8 w-8 rounded-md" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      {boards?.map((board) => (
        <Tooltip key={board.id}>
          <TooltipTrigger asChild>
            <Link to={`/boards/${board.id}`}>
              <Button
                variant={boardId === board.id ? "secondary" : "ghost"}
                size="icon"
                className="h-8 w-8 text-xs font-bold"
                style={board.brandColor ? { color: board.brandColor } : undefined}
              >
                {board.issuePrefix?.slice(0, 2) || board.name.slice(0, 2).toUpperCase()}
              </Button>
            </Link>
          </TooltipTrigger>
          <TooltipContent side="right">{board.name}</TooltipContent>
        </Tooltip>
      ))}
    </div>
  );
}
