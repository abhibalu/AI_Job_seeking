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


import time
import logging

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log every request and response in structured JSON.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            logger.info(
                "Request processed",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "client_ip": request.client.host if request.client else "unknown",
                    "duration": f"{process_time:.4f}s",
                    "status_code": response.status_code
                }
            )
            
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                "Request failed",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "client_ip": request.client.host if request.client else "unknown",
                    "duration": f"{process_time:.4f}s",
                    "error": str(e)
                },
                exc_info=True
            )
            raise e
