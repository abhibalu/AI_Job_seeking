from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from langfuse import Langfuse
from backend.settings import settings

# Initialize Langfuse client (globally or per request, global is better for connection pooling if applicable)
# It picks up env vars automatically
langfuse = Langfuse()

class LangfuseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        
        trace_name = f"{request.method} {request.url.path}"
        
        # Start a trace using the client (Langfuse v2)
        trace = langfuse.trace(
            name=trace_name,
            input={
                "method": request.method,
                "url": str(request.url),
                "query_params": dict(request.query_params)
            },
            metadata={
                "client": request.client.host if request.client else "unknown"
            }
        )
        
        try:
            response = await call_next(request)
            
            trace.update(
                output={"status_code": response.status_code},
            )
            return response
        except Exception as e:
            trace.update(level="ERROR", status_message=str(e))
            raise e
