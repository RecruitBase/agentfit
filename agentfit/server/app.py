"""
FastAPI Application for AgentFit.

Provides REST API for submitting evaluation requests, retrieving results,
and managing Business Need Profiles.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import json
from loguru import logger

from agentfit.bnp.schema import BNPProfile
from agentfit.bnp.parser import BNPParser
from agentfit.core.evaluator import Evaluator, EvaluationRequest, EvaluationResult
from agentfit.core.dimension import DimensionRegistry
from agentfit.interpretability.config import InterpretabilityConfig, LLMProvider


class InterpretabilityModel(BaseModel):
    """API model for interpretability configuration."""
    enabled: bool = Field(True, description="Enable LLM interpretation")
    provider: str = Field("openai", description="LLM provider: openai, anthropic, or google")
    api_key: str = Field(..., description="API key for the LLM provider")
    model: Optional[str] = Field(None, description="Model name (uses provider default if omitted)")
    temperature: float = Field(0.3, ge=0.0, le=2.0, description="Generation temperature")
    include_recommendations: bool = Field(True, description="Include actionable recommendations")


# Pydantic models for API
class EvaluationRequestModel(BaseModel):
    """API model for evaluation requests."""
    agent_id: str = Field(..., description="Unique agent identifier")
    agent_interface: Optional[Dict[str, Any]] = Field(None, description="Agent interface spec")
    scenario: Dict[str, Any] = Field(..., description="Test scenario")
    bnp_profile_id: Optional[str] = Field(None, description="BNP profile ID to use")
    dimensions: Optional[List[str]] = Field(None, description="Specific dimensions to evaluate")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    interpretability: Optional[InterpretabilityModel] = Field(
        None, description="LLM interpretability config (omit to skip interpretation)"
    )


class BNPProfileModel(BaseModel):
    """API model for BNP profiles."""
    name: str
    organization: str
    description: Optional[str] = None
    agent_domain: str = "general"
    requirements: List[Dict[str, Any]] = Field(default_factory=list)
    evaluation_dimensions: List[Dict[str, Any]] = Field(default_factory=list)
    compliance_requirements: Optional[List[str]] = None


class DimensionInfo(BaseModel):
    """Information about an available dimension."""
    dimension_id: str
    dimension_name: str
    description: str
    scoring_method: str


# In-memory storage (replace with database in production)
_evaluations: Dict[str, EvaluationResult] = {}
_bnp_profiles: Dict[str, BNPProfile] = {}
_evaluation_history: List[Dict[str, Any]] = []


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="AgentFit",
        description="Enterprise-grade agent evaluation framework",
        version="0.1.0",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize evaluator
    evaluator = Evaluator()
    
    # Health check
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "agentfit",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    # Dimensions endpoints
    @app.get("/api/dimensions")
    async def list_dimensions() -> List[DimensionInfo]:
        """List available evaluation dimensions."""
        dimensions = []
        for dim_id in DimensionRegistry.list_available():
            dim_class = DimensionRegistry.get(dim_id)
            if dim_class:
                dimensions.append(
                    DimensionInfo(
                        dimension_id=dim_class.dimension_id,
                        dimension_name=dim_class.dimension_name,
                        description=dim_class.description,
                        scoring_method=dim_class.scoring_method.value,
                    )
                )
        return dimensions
    
    # BNP Profile endpoints
    @app.post("/api/bnp-profiles")
    async def create_bnp_profile(profile_data: BNPProfileModel):
        """Create a new BNP profile."""
        try:
            profile = BNPProfile(
                name=profile_data.name,
                organization=profile_data.organization,
                description=profile_data.description or "",
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat(),
            )
            
            _bnp_profiles[profile.id] = profile
            
            logger.info(f"Created BNP profile: {profile.id}")
            
            return {
                "id": profile.id,
                "name": profile.name,
                "organization": profile.organization,
                "created_at": profile.created_at,
            }
        except Exception as e:
            logger.error(f"Error creating BNP profile: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.post("/api/bnp-profiles/upload")
    async def upload_bnp_profile(file: UploadFile = File(...)):
        """Upload and parse a BNP profile from markdown file."""
        try:
            content = await file.read()
            markdown_content = content.decode("utf-8")
            
            profile = BNPParser.parse_markdown(markdown_content)
            _bnp_profiles[profile.id] = profile
            
            logger.info(f"Uploaded BNP profile: {profile.id}")
            
            return {
                "id": profile.id,
                "name": profile.name,
                "organization": profile.organization,
                "requirements": len(profile.requirements),
                "dimensions": len(profile.evaluation_dimensions),
            }
        except Exception as e:
            logger.error(f"Error uploading BNP profile: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.get("/api/bnp-profiles/{profile_id}")
    async def get_bnp_profile(profile_id: str):
        """Retrieve a BNP profile."""
        if profile_id not in _bnp_profiles:
            raise HTTPException(status_code=404, detail="BNP profile not found")
        
        profile = _bnp_profiles[profile_id]
        return profile.__dict__
    
    @app.get("/api/bnp-profiles")
    async def list_bnp_profiles():
        """List all BNP profiles."""
        return [
            {
                "id": p.id,
                "name": p.name,
                "organization": p.organization,
                "created_at": p.created_at,
            }
            for p in _bnp_profiles.values()
        ]
    
    # Evaluation endpoints
    @app.post("/api/evaluate")
    async def submit_evaluation(
        request_data: EvaluationRequestModel,
        background_tasks: BackgroundTasks
    ):
        """Submit an evaluation request."""
        try:
            # Validate and get BNP if specified
            bnp = None
            if request_data.bnp_profile_id:
                if request_data.bnp_profile_id not in _bnp_profiles:
                    raise HTTPException(status_code=404, detail="BNP profile not found")
                bnp = _bnp_profiles[request_data.bnp_profile_id]
            
            # Build interpretability config if provided
            interp_config = None
            if request_data.interpretability:
                interp_config = InterpretabilityConfig(
                    enabled=request_data.interpretability.enabled,
                    provider=LLMProvider(request_data.interpretability.provider.lower()),
                    api_key=request_data.interpretability.api_key,
                    model=request_data.interpretability.model,
                    temperature=request_data.interpretability.temperature,
                    include_recommendations=request_data.interpretability.include_recommendations,
                )

            # Create evaluation request
            eval_request = EvaluationRequest(
                agent_id=request_data.agent_id,
                agent_interface=request_data.agent_interface or {},
                scenario=request_data.scenario,
                bnp_profile=bnp,
                dimensions=request_data.dimensions,
                context=request_data.context or {},
                interpretability=interp_config,
            )
            
            # Generate evaluation ID
            eval_id = str(uuid.uuid4())
            
            # Run evaluation (in background for real async)
            async def run_evaluation():
                try:
                    result = await evaluator.evaluate(eval_request)
                    result.id = eval_id
                    _evaluations[eval_id] = result
                    _evaluation_history.append({
                        "eval_id": eval_id,
                        "agent_id": request_data.agent_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "completed",
                        "score": result.overall_score,
                    })
                    logger.info(f"Evaluation completed: {eval_id}")
                except Exception as e:
                    logger.error(f"Evaluation error: {e}")
                    _evaluation_history.append({
                        "eval_id": eval_id,
                        "agent_id": request_data.agent_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "failed",
                        "error": str(e),
                    })
            
            # Schedule background task
            background_tasks.add_task(run_evaluation)
            
            logger.info(f"Evaluation submitted: {eval_id}")
            
            return {
                "evaluation_id": eval_id,
                "agent_id": request_data.agent_id,
                "status": "submitted",
                "created_at": datetime.utcnow().isoformat(),
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error submitting evaluation: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.get("/api/evaluations/{eval_id}")
    async def get_evaluation(eval_id: str):
        """Retrieve an evaluation result."""
        if eval_id not in _evaluations:
            # Check history to see if it's still processing
            history_entry = next(
                (h for h in _evaluation_history if h["eval_id"] == eval_id),
                None
            )
            if history_entry:
                if history_entry["status"] == "completed":
                    raise HTTPException(status_code=404, detail="Evaluation result not found")
                else:
                    return {
                        "evaluation_id": eval_id,
                        "status": history_entry["status"],
                    }
            raise HTTPException(status_code=404, detail="Evaluation not found")
        
        result = _evaluations[eval_id]
        return result.to_dict()
    
    @app.get("/api/evaluations")
    async def list_evaluations(agent_id: Optional[str] = None):
        """List evaluations with optional filtering."""
        results = []
        for eval_id, result in _evaluations.items():
            if agent_id and result.agent_id != agent_id:
                continue
            results.append({
                "evaluation_id": eval_id,
                "agent_id": result.agent_id,
                "scenario_id": result.scenario_id,
                "overall_score": result.overall_score,
                "passed": result.passed,
                "created_at": result.created_at,
            })
        return results
    
    # Stats endpoint
    @app.get("/api/stats")
    async def get_stats():
        """Get system statistics."""
        return {
            "total_evaluations": len(_evaluations),
            "total_bnp_profiles": len(_bnp_profiles),
            "available_dimensions": len(DimensionRegistry.list_available()),
            "dimensions": DimensionRegistry.list_available(),
        }
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
