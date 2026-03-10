export interface VultrPlan {
  id: string;
  vcpu_count: number;
  ram: number;
  disk: number;
  monthly_cost: number;
  type: string;
  locations: string[];
}

export interface VultrRegion {
  id: string;
  city: string;
  country: string;
  continent: string;
}

export interface VultrOs {
  id: number;
  name: string;
  family: string;
}

export interface VultrInstance {
  id: string;
  label: string;
  os: string;
  ram: number;
  disk: number;
  main_ip: string;
  vcpu_count: number;
  region: string;
  plan: string;
  status: string;
  power_status: string;
  server_status: string;
  default_password: string;
  date_created: string;
}

export interface CreateInstanceOpts {
  label: string;
  region: string;
  plan: string;
  os_id: number;
  hostname?: string;
  tag?: string;
  script_id?: string;
}
