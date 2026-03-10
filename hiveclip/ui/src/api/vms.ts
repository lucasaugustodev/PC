import type { Vm } from "@hiveclip/shared";
import { api } from "./client.js";

export const fetchVm = async (boardId: string): Promise<Vm | null> => {
  try {
    return await api.get<Vm>(`/boards/${boardId}/vm`);
  } catch {
    return null;
  }
};
export const provisionVm = (boardId: string) => api.post(`/boards/${boardId}/vm/provision`);
export const startVm = (boardId: string) => api.post(`/boards/${boardId}/vm/start`);
export const stopVm = (boardId: string) => api.post(`/boards/${boardId}/vm/stop`);
export const rebootVm = (boardId: string) => api.post(`/boards/${boardId}/vm/reboot`);
export const reprovisionVm = (boardId: string) => api.post(`/boards/${boardId}/vm/reprovision`);
export const destroyVm = (boardId: string) => api.delete(`/boards/${boardId}/vm`);
