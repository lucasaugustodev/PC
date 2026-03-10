import type { Board, CreateBoardInput, UpdateBoardInput } from "@hiveclip/shared";
import { api } from "./client.js";
export const fetchBoards = () => api.get<Board[]>("/boards");
export const fetchBoard = (id: string) => api.get<Board>(`/boards/${id}`);
export const createBoard = (data: CreateBoardInput) => api.post<Board>("/boards", data);
export const updateBoard = (id: string, data: UpdateBoardInput) => api.patch<Board>(`/boards/${id}`, data);
export const deleteBoard = (id: string) => api.delete(`/boards/${id}`);
