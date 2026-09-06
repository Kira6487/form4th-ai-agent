import { KnowledgeSourceDetail } from "../../../../../../components/knowledge-source-detail";

export default async function KnowledgeSourcePage({ params }: { params: Promise<{ id: string; sourceId: string }> }) { const { id, sourceId } = await params; return <KnowledgeSourceDetail companyId={id} sourceId={sourceId} />; }
