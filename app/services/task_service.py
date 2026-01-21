
import os
from supabase import create_client, Client

class TaskService:
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise ValueError("Supabase credentials missing")
        self.client: Client = create_client(url, key)

    async def create_task(self, description: str, agent_id: str | None = None, user_id: str | None = None) -> dict:
        """Create a new task in the ai_jobs table."""
        data = {
            "agent_id": agent_id,
            "job_type": "task",
            "input_data": {"description": description},
            "status": "pending",
            "user_id": user_id
        }
        
        try:
            response = self.client.table("ai_jobs").insert(data).execute()
            if response.data:
                return response.data[0]
            raise Exception("No data returned from insert")
        except Exception as e:
            # Re-raise or handle? For now, re-raise to be caught by caller or test
            raise e
