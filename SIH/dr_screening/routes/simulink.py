"""Simulink Simulation Route for District-Level Telemedicine Screening (SIH26038).

Independent API endpoint serving simulation computations for resource allocation,
bandwidth constraints, AI server throughput, and doctor review queues.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

from dr_screening.services.simulation_engine import run_simulation

router = APIRouter(prefix="/api/simulink", tags=["Simulink Workflow Simulation"])


class SimulationRequest(BaseModel):
    district_population: int = Field(default=1000000, description="Total district population")
    diabetic_population: int = Field(default=100000, description="Estimated diabetic patient pool")
    patients_per_day: int = Field(default=333, description="Target daily screening arrivals")
    bandwidth: str = Field(default="10 Mbps", description="Network uplink bandwidth at PHCs")
    phcs: int = Field(default=25, description="Number of participating Primary Health Centers")
    cameras: int = Field(default=2, description="Fundus cameras allocated per PHC")
    technicians: int = Field(default=2, description="Certified screening technicians per PHC")
    ai_servers: int = Field(default=3, description="Active AI inference server nodes")
    doctors: int = Field(default=5, description="Consulting ophthalmologists on tele-triage duty")
    working_days: int = Field(default=300, description="Annual clinic operational days")


@router.post("/simulate")
def simulate_pipeline(config: SimulationRequest = Body(...)) -> Dict[str, Any]:
    """Execute district telemedicine DR screening pipeline simulation."""
    return run_simulation(config.model_dump())
