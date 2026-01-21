
from app.rag.knowledge_vault import ingest_document_content

class ContentService:
    def __init__(self):
        # We might need Supabase client if we do direct DB ops, but knowledge_vault handles it.
        pass

    async def save_content(self, title: str, content: str, agent_id: str) -> dict:
        """Save generated content to the Knowledge Vault.
        
        Args:
            title: Title of the content.
            content: The text content.
            agent_id: ID of the agent creating the content.
            
        Returns:
            Dictionary with result (success, ids, etc).
        """
        # We delegate to the existing RAG knowledge vault ingestion
        # content is stored in 'embeddings' table (chunks) and 'agent_knowledge'? 
        # Actually ingest_document_content stores in embeddings table. 
        # For a CMS, this is okay for now as it makes it searchable.
        
        result = await ingest_document_content(
            content=content,
            title=title,
            document_type="generated_content",
            agent_id=agent_id
        )
        return result
