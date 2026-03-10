import type { CreateInstanceOpts, VultrInstance, VultrOs, VultrPlan, VultrRegion } from "./types.js";

const BASE = "https://api.vultr.com/v2";

export class VultrClient {
  private apiKey: string;

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  private headers(): HeadersInit {
    return {
      Authorization: `Bearer ${this.apiKey}`,
      "Content-Type": "application/json",
    };
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${BASE}${path}`, {
      method,
      headers: this.headers(),
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Vultr API ${method} ${path} failed (${res.status}): ${text}`);
    }
    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
  }

  async listPlans(): Promise<VultrPlan[]> {
    const data = await this.request<{ plans: VultrPlan[] }>("GET", "/plans");
    return data.plans;
  }

  async listRegions(): Promise<VultrRegion[]> {
    const data = await this.request<{ regions: VultrRegion[] }>("GET", "/regions");
    return data.regions;
  }

  async listOs(): Promise<VultrOs[]> {
    const data = await this.request<{ os: VultrOs[] }>("GET", "/os");
    return data.os;
  }

  async createInstance(opts: CreateInstanceOpts): Promise<VultrInstance> {
    const data = await this.request<{ instance: VultrInstance }>("POST", "/instances", opts);
    return data.instance;
  }

  async getInstance(id: string): Promise<VultrInstance> {
    const data = await this.request<{ instance: VultrInstance }>("GET", `/instances/${id}`);
    return data.instance;
  }

  async deleteInstance(id: string): Promise<void> {
    await this.request<void>("DELETE", `/instances/${id}`);
  }

  async startInstance(id: string): Promise<void> {
    await this.request<void>("POST", `/instances/${id}/start`);
  }

  async stopInstance(id: string): Promise<void> {
    await this.request<void>("POST", `/instances/${id}/halt`);
  }

  async rebootInstance(id: string): Promise<void> {
    await this.request<void>("POST", `/instances/${id}/reboot`);
  }

  async getBestWindowsPlan(region?: string): Promise<VultrPlan | null> {
    const plans = await this.listPlans();
    const eligible = plans
      .filter((p) => p.type === "vc2")
      .filter((p) => p.monthly_cost <= 60)
      .filter((p) => !region || p.locations.includes(region))
      .sort((a, b) => {
        const aScore = a.ram / a.monthly_cost;
        const bScore = b.ram / b.monthly_cost;
        return bScore - aScore;
      });
    return eligible[0] ?? null;
  }

  async getBestRegion(): Promise<VultrRegion | null> {
    const regions = await this.listRegions();
    // Prefer US regions
    const us = regions.filter((r) => r.country === "US");
    return us[0] ?? regions[0] ?? null;
  }
}
