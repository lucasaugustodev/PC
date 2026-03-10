import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { fetchBoards, createBoard } from "../api/boards";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "../components/ui/dialog";
import { VmStatusBadge } from "../components/VmStatusBadge";
import { Plus, Hexagon } from "lucide-react";

export function BoardListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: boards, isLoading } = useQuery({ queryKey: ["boards"], queryFn: fetchBoards });
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const mutation = useMutation({
    mutationFn: () => createBoard({ name, description: description || undefined }),
    onSuccess: (board) => {
      queryClient.invalidateQueries({ queryKey: ["boards"] });
      setOpen(false);
      setName("");
      setDescription("");
      navigate(`/boards/${board.id}`);
    },
  });

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Your Boards</h1>
          <p className="text-muted-foreground text-sm">Each board runs on a dedicated Windows VM</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="mr-2 h-4 w-4" />New Board</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Board</DialogTitle>
            </DialogHeader>
            <form onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="board-name">Name</Label>
                <Input id="board-name" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
              </div>
              <div className="space-y-2">
                <Label htmlFor="board-desc">Description</Label>
                <Input id="board-desc" value={description} onChange={(e) => setDescription(e.target.value)} />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={mutation.isPending}>
                  {mutation.isPending ? "Creating..." : "Create Board"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse h-32" />
          ))}
        </div>
      ) : boards?.length === 0 ? (
        <Card className="p-12 text-center">
          <Hexagon className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">No boards yet. Create your first one.</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {boards?.map((board) => (
            <Card
              key={board.id}
              className="cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => navigate(`/boards/${board.id}`)}
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{board.name}</CardTitle>
                  <VmStatusBadge status={board.status} />
                </div>
                {board.description && <CardDescription>{board.description}</CardDescription>}
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">
                  Prefix: {board.issuePrefix} &middot; Created {new Date(board.createdAt).toLocaleDateString()}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
