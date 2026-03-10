import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.pipeline_graph import build_pipeline_graph
from agents.supabase_checkpointer import SupabaseSaver
from agents.supabase_client import get_supabase_client

supabase_client = get_supabase_client()
checkpointer = SupabaseSaver(supabase_client)
graph = build_pipeline_graph().compile(checkpointer=checkpointer)

# Generating a diagram of the LangGraph state machine.
png_bytes = graph.get_graph(xray=True).draw_mermaid_png()
with open('/Users/abhijithm/.gemini/antigravity/brain/51edb658-11c8-42d5-bcbd-0cee6b52b564/langgraph_diagram.png', 'wb') as f:
    f.write(png_bytes)
print("Diagram saved to brain artifact folder.")
