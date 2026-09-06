import { LeadListView } from "../../../../../components/lead-list-view";

export default async function LeadsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <LeadListView companyId={id} />;
}
