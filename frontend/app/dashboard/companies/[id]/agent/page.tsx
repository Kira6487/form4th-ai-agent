import { AgentView } from "../../../../../components/agent-view";

export default async function CompanyAgentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AgentView companyId={id} />;
}
