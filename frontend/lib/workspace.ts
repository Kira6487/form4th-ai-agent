import { apiFetch } from "../services/api/client";
import type { Company, CompanyInput, CompanyUpdate, Organization } from "../types/workspace";

export function getOrganizations(): Promise<Organization[]> {
  return apiFetch<Organization[]>("/api/v1/organizations");
}

export function createOrganization(name: string): Promise<Organization> {
  return apiFetch<Organization>("/api/v1/organizations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export function getCompanies(organizationId: string): Promise<Company[]> {
  return apiFetch<Company[]>(`/api/v1/organizations/${organizationId}/companies`);
}

export function getCompany(organizationId: string, companyId: string): Promise<Company> {
  return apiFetch<Company>(`/api/v1/organizations/${organizationId}/companies/${companyId}`);
}

export function createCompany(organizationId: string, input: CompanyInput): Promise<Company> {
  return apiFetch<Company>(`/api/v1/organizations/${organizationId}/companies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function updateCompany(organizationId: string, companyId: string, input: CompanyUpdate): Promise<Company> {
  return apiFetch<Company>(`/api/v1/organizations/${organizationId}/companies/${companyId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}
