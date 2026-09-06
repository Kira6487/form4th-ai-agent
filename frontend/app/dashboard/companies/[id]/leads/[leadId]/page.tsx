import { LeadDetailView } from "../../../../../../components/lead-detail-view";

export default async function LeadPage({ params }: { params: Promise<{ id: string; leadId: string }> }) {
  const { id, leadId } = await params;
  return <LeadDetailView companyId={id} leadId={leadId} />;
}
