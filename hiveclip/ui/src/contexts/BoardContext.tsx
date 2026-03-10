import { createContext, useContext, useState, type ReactNode } from "react";

interface BoardContextValue {
  activeBoardId: string | null;
  setActiveBoardId: (id: string | null) => void;
}

const BoardContext = createContext<BoardContextValue | null>(null);

export function BoardProvider({ children }: { children: ReactNode }) {
  const [activeBoardId, setActiveBoardId] = useState<string | null>(null);

  return (
    <BoardContext.Provider value={{ activeBoardId, setActiveBoardId }}>
      {children}
    </BoardContext.Provider>
  );
}

export function useBoard() {
  const ctx = useContext(BoardContext);
  if (!ctx) throw new Error("useBoard must be used within BoardProvider");
  return ctx;
}
