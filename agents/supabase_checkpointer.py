"""
Custom LangGraph Checkpointer using the synchronous Supabase Python client.

Implements `BaseCheckpointSaver` to persist graph state in Supabase.
This allows the graph to pause, resume, and survive server restarts without losing state.
"""
import logging
from typing import Iterator, Optional, Any
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    SerializerProtocol,
)
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from supabase import Client

from backend.settings import settings

logger = logging.getLogger(__name__)


class SupabaseSaver(BaseCheckpointSaver):
    """
    A persistent checkpointer for LangGraph using Supabase.
    Stores checkpoints and writes in three tables:
      - langgraph_checkpoints
      - langgraph_checkpoint_blobs
      - langgraph_checkpoint_writes
    """

    def __init__(
        self,
        client: Client,
        *,
        serde: Optional[SerializerProtocol] = None,
    ):
        super().__init__(serde=serde or JsonPlusSerializer())
        self.client = client

    def get_tuple(self, config: dict) -> Optional[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id")
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        query = self.client.table("langgraph_checkpoints").select("*").eq("thread_id", thread_id).eq("checkpoint_ns", checkpoint_ns)

        if checkpoint_id:
            query = query.eq("checkpoint_id", checkpoint_id)
        else:
            query = query.order("checkpoint_id", desc=True).limit(1)

        result = query.execute()
        if not result.data:
            return None

        row = result.data[0]
        
        # Load associated writes
        writes_query = (
            self.client.table("langgraph_checkpoint_writes")
            .select("task_id, channel, type, blob")
            .eq("thread_id", thread_id)
            .eq("checkpoint_ns", checkpoint_ns)
            .eq("checkpoint_id", row["checkpoint_id"])
            .execute()
        )
        
        pending_writes = [
            (
                w["task_id"],
                w["channel"],
                self.serde.loads_typed((w["type"], bytes.fromhex(w["blob"]))),
            )
            for w in (writes_query.data or [])
        ]

        checkpoint = self.serde.loads_typed((row["type"], bytes.fromhex(row["checkpoint"])))
        metadata = row.get("metadata", {})
        
        parent_config = None
        if row.get("parent_checkpoint_id"):
            parent_config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": row["parent_checkpoint_id"],
                }
            }

        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": row["checkpoint_id"],
                }
            },
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=parent_config,
            pending_writes=pending_writes,
        )

    def list(
        self,
        config: dict,
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[dict] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        """List checkpoints from the database."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        
        query = self.client.table("langgraph_checkpoints").select("*").eq("thread_id", thread_id).eq("checkpoint_ns", checkpoint_ns)
        
        if before:
            query = query.lt("checkpoint_id", before["configurable"]["checkpoint_id"])
            
        if filter:
            for k, v in filter.items():
                query = query.eq(f"metadata->>{k}", str(v))
                
        query = query.order("checkpoint_id", desc=True)
        
        if limit is not None:
            query = query.limit(limit)
            
        result = query.execute()
        for row in (result.data or []):
            yield self.get_tuple({
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": row["checkpoint_id"]
                }
            })

    def put(
        self,
        config: dict,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, str],
    ) -> dict:
        """Store a checkpoint to the database."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        
        type_, serialized_checkpoint = self.serde.dumps_typed(checkpoint)
        
        row = {
            "thread_id": thread_id,
            "checkpoint_ns": checkpoint_ns,
            "checkpoint_id": checkpoint["id"],
            "parent_checkpoint_id": config["configurable"].get("checkpoint_id"),
            "type": type_,
            "checkpoint": serialized_checkpoint.hex(),
            "metadata": metadata,
        }
        
        self.client.table("langgraph_checkpoints").upsert(row).execute()
        
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
            }
        }

    def put_writes(self, config: dict, writes: list[tuple[str, str, Any]], task_id: str) -> None:
        """Store intermediate writes to the database."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]

        rows = []
        for idx, (channel, value) in enumerate(writes):
            type_, serialized_value = self.serde.dumps_typed(value)
            rows.append({
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
                "task_id": task_id,
                "idx": idx,
                "channel": channel,
                "type": type_,
                "blob": serialized_value.hex(),
            })

        if rows:
            self.client.table("langgraph_checkpoint_writes").upsert(rows).execute()
