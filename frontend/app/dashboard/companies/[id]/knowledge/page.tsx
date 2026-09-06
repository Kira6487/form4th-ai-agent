import { KnowledgeView } from "../../../../../components/knowledge-view";

export default async function CompanyKnowledgePage({ params }: { params: Promise<{ id: string }> }) { const { id } = await params; return <KnowledgeView companyId={id} />; }
