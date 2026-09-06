import { KnowledgeForm } from "../../../../../../components/knowledge-form";

export default async function NewKnowledgePage({ params }: { params: Promise<{ id: string }> }) { const { id } = await params; return <KnowledgeForm companyId={id} />; }
