from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import logging
from datetime import datetime
from pathlib import Path

from classifier import TicketClassifier
from models import TicketInput, ClassificationResponse
from config import Config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI-Powered Support Ticket Classifier",
    description="""
    An intelligent support ticket classification system with advanced LLM engineering:
    
    Features:
    - 🛡️ **System Prompt Hardening**: Detects and blocks prompt injection attempts
    - 🔒 **PII Detection/Redaction**: Automatically redacts sensitive information
    - ✅ **LLM Guard**: Comprehensive input/output validation
    - 📊 **Structured Output**: Pydantic-validated JSON responses
    - 🔄 **Fallback/Retry**: Automatic retry with exponential backoff
    - 💰 **Cost Calculation**: Real-time token usage and cost tracking
    - 📝 **Prompt Versioning**: Multiple prompt versions with A/B testing support
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for web interface
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize classifier on module load
try:
    classifier = TicketClassifier()
    logger.info("✓ Ticket Classifier initialized successfully")
    logger.info(f"  Model: {classifier.model_name}")
    logger.info(f"  Prompt Version: {classifier.prompt_version}")
    logger.info(f"  PII Redaction: {classifier.enable_pii_redaction}")
    logger.info(f"  Cost Tracking: {classifier.enable_cost_tracking}")
except Exception as e:
    logger.error(f"✗ Failed to initialize classifier: {e}")
    classifier = None


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - redirect to docs or serve demo UI"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Support Ticket Classifier</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 40px;
                backdrop-filter: blur(10px);
            }
            h1 { margin-top: 0; font-size: 2.5em; }
            .feature { margin: 15px 0; padding: 10px; background: rgba(255, 255, 255, 0.1); border-radius: 8px; }
            .links { margin-top: 30px; }
            a {
                display: inline-block;
                margin: 10px 10px 10px 0;
                padding: 12px 24px;
                background: white;
                color: #667eea;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                transition: transform 0.2s;
            }
            a:hover { transform: translateY(-2px); }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎫 AI Support Ticket Classifier</h1>
            <p>Intelligent ticket classification with advanced LLM engineering</p>
            
            <div class="feature">🛡️ <strong>System Prompt Hardening</strong> - Blocks injection attempts</div>
            <div class="feature">🔒 <strong>PII Detection/Redaction</strong> - Protects sensitive data</div>
            <div class="feature">✅ <strong>LLM Guard</strong> - Input/output validation</div>
            <div class="feature">📊 <strong>Structured Output</strong> - Validated JSON responses</div>
            <div class="feature">🔄 <strong>Fallback/Retry</strong> - Automatic error recovery</div>
            <div class="feature">💰 <strong>Cost Calculation</strong> - Real-time cost tracking</div>
            <div class="feature">📝 <strong>Prompt Versioning</strong> - A/B testing support</div>
            
            <div class="links">
                <a href="/demo">📱 Try Demo</a>
                <a href="/docs">📚 API Docs</a>
                <a href="/health">💚 Health Check</a>
                <a href="/stats">📊 Statistics</a>
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/demo", response_class=HTMLResponse)
async def demo_ui():
    """Serve the demo UI"""
    demo_path = Path("demo_ui/index.html")
    if demo_path.exists():
        return HTMLResponse(content=demo_path.read_text(), status_code=200)
    else:
        raise HTTPException(status_code=404, detail="Demo UI not found")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "model": classifier.model_name if classifier else None,
        "prompt_version": classifier.prompt_version if classifier else None,
        "features": {
            "pii_redaction": classifier.enable_pii_redaction if classifier else None,
            "cost_tracking": classifier.enable_cost_tracking if classifier else None
        }
    }


@app.post("/classify", response_model=ClassificationResponse)
async def classify_ticket(ticket: TicketInput):
    """
    Classify a support ticket.
    
    This endpoint performs comprehensive classification with security features:
    - Validates and sanitizes input
    - Detects and blocks prompt injection attempts
    - Redacts PII (emails, credit cards, phone numbers, etc.)
    - Returns structured classification with confidence scores
    - Tracks token usage and estimated costs
    
    Returns a detailed classification including:
    - Issue category (delivery_issue, payment_issue, etc.)
    - Assigned team (logistics_team, payments_team, etc.)
    - Priority level (low, medium, high, critical)
    - Customer sentiment (positive, neutral, negative, angry)
    - Confidence score (0.0 to 1.0)
    - Reasoning for the classification
    - Flag for human review if needed
    """
    try:
        logger.info(f"Received classification request: subject='{ticket.subject[:50]}...'")
        
        result = classifier.classify_ticket(ticket)
        
        logger.info(
            f"Classification complete: "
            f"category={result.classification.issue_category}, "
            f"priority={result.classification.priority}"
        )
        
        return result
        
    except ValueError as e:
        # Input validation errors (e.g., injection blocked, PII issues)
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        # Unexpected errors
        logger.error(f"Classification error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during classification"
        )


@app.post("/classify/simple")
async def classify_simple(subject: str, message: str, source: str = "web_form"):
    """
    Simplified classification endpoint (non-Pydantic).
    
    Query parameters:
    - subject: Ticket subject
    - message: Ticket message
    - source: Ticket source (email, web_form, chat)
    """
    try:
        ticket = TicketInput(subject=subject, message=message, source=source)
        return await classify_ticket(ticket)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/stats")
async def get_statistics():
    """
    Get system statistics including:
    - Cost tracking (total tokens, costs, average per request)
    - Retry statistics (success rate, retry counts)
    - Classifier configuration
    """
    try:
        stats = classifier.get_statistics()
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"Error retrieving statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@app.get("/config")
async def get_configuration():
    """Get current classifier configuration"""
    return {
        "model": classifier.model_name,
        "prompt_version": classifier.prompt_version,
        "features": {
            "pii_redaction": classifier.enable_pii_redaction,
            "cost_tracking": classifier.enable_cost_tracking
        },
        "available_categories": Config.ISSUE_CATEGORIES,
        "available_teams": Config.ASSIGNED_TEAMS,
        "priorities": Config.PRIORITIES,
        "sentiments": Config.SENTIMENTS,
        "retry_config": {
            "max_retries": Config.MAX_RETRIES,
            "retry_delay": Config.RETRY_DELAY
        }
    }


@app.get("/prompts/versions")
async def list_prompt_versions():
    """List available prompt versions"""
    return {
        "current_version": classifier.prompt_manager.current_version,
        "available_versions": classifier.prompt_manager.list_versions()
    }


@app.get("/prompts/{version}")
async def get_prompt_details(version: str):
    """Get details about a specific prompt version"""
    try:
        metadata = classifier.prompt_manager.get_version_metadata(version)
        return metadata
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    print("="*70)
    print("🚀 Starting AI-Powered Support Ticket Classifier API")
    print("="*70)
    print(f"Model: {Config.MODEL_NAME}")
    print(f"Prompt Version: {Config.PROMPT_VERSION}")
    print(f"PII Redaction: {Config.PII_REDACTION_ENABLED}")
    print(f"Cost Tracking: {Config.COST_TRACKING_ENABLED}")
    print("="*70)
    print("\nServer will start at: http://127.0.0.1:5178")
    print("API Documentation: http://127.0.0.1:5178/docs")
    print("Demo Interface: http://127.0.0.1:5178/demo")
    print("\nPress CTRL+C to stop the server")
    print("="*70)
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=5178,
        log_level="info"
    )
