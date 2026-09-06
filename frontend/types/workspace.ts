export type Organization = {
  id: string;
  name: string;
  slug: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type Company = {
  id: string;
  organization_id: string;
  name: string;
  legal_name: string | null;
  website: string | null;
  description: string | null;
  industry: string | null;
  country: string | null;
  timezone: string | null;
  status: "active" | "inactive" | "archived";
  created_at: string;
  updated_at: string;
};

export type CompanyInput = Omit<Company, "id" | "organization_id" | "status" | "created_at" | "updated_at">;
export type CompanyUpdate = Partial<CompanyInput> & { status?: Company["status"] };
