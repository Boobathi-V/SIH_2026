"""Simulation Engine for District-Level Telemedicine DR Screening Pipeline (SIH26038).

Models healthcare resource allocation, bandwidth constraints, AI server throughput,
rejection gateway statistics, ophthalmologist review queues, and annual district capacity.
"""

from typing import Dict, Any, List
import math


def run_simulation(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run discrete-event analytical simulation of the telemedicine pipeline.
    
    Args:
        config: Dictionary containing district population, infrastructure, and resources.
    
    Returns:
        Structured simulation results containing KPIs, queue statistics, gateway rates,
        capacity estimations, bottleneck identification, and optimization recommendations.
    """
    # District Demographics
    district_pop = int(config.get("district_population", 1000000))
    diabetic_pop = int(config.get("diabetic_population", 100000))
    patients_per_day = int(config.get("patients_per_day", 333))
    working_days = int(config.get("working_days", 300))

    # Resources
    phcs = max(1, int(config.get("phcs", 25)))
    cameras = max(1, int(config.get("cameras", 2)))
    technicians = max(1, int(config.get("technicians", 2)))
    ai_servers = max(1, int(config.get("ai_servers", 3)))
    doctors = max(1, int(config.get("doctors", 5)))
    
    # Bandwidth in Mbps
    raw_bw = str(config.get("bandwidth", "10 Mbps"))
    bw_mbps = float(raw_bw.lower().replace("mbps", "").strip()) if "mbps" in raw_bw.lower() else 10.0
    if bw_mbps <= 0:
        bw_mbps = 10.0

    # Image Characteristics
    image_size_mb = float(config.get("image_size_mb", 3.2))
    compression_ratio = float(config.get("compression_ratio", 0.35))  # JPEG 85 compression
    effective_img_mb = image_size_mb * compression_ratio
    effective_img_mbit = effective_img_mb * 8.0

    # Section 3: Quality Rejection Gateway Modeling (Real-world clinical audit distribution)
    # Rejection rate typically 12-18% in rural fundus imaging without pupil dilation
    blur_rate = float(config.get("blur_rate", 0.05))
    low_illum_rate = float(config.get("low_illumination_rate", 0.04))
    over_exp_rate = float(config.get("over_exposure_rate", 0.02))
    poor_focus_rate = float(config.get("poor_focus_rate", 0.03))
    uncentered_rate = float(config.get("uncentered_retina_rate", 0.02))
    low_res_rate = float(config.get("low_resolution_rate", 0.01))

    # Total combined rejection probability (accounting for overlap)
    raw_rejection_rate = blur_rate + low_illum_rate + over_exp_rate + poor_focus_rate + uncentered_rate + low_res_rate
    rejection_rate = min(0.35, max(0.04, raw_rejection_rate))
    
    total_images_captured = patients_per_day * 2  # 2 eyes per patient
    rejected_images = int(round(total_images_captured * rejection_rate))
    accepted_images = total_images_captured - rejected_images

    # Rejection Breakdown
    rejection_reasons = [
        {"reason": "Motion Blur", "count": int(round(rejected_images * (blur_rate / raw_rejection_rate))), "percentage": round(blur_rate / raw_rejection_rate * 100, 1)},
        {"reason": "Low Illumination / Underexposure", "count": int(round(rejected_images * (low_illum_rate / raw_rejection_rate))), "percentage": round(low_illum_rate / raw_rejection_rate * 100, 1)},
        {"reason": "Over Exposure / Flash Artifact", "count": int(round(rejected_images * (over_exp_rate / raw_rejection_rate))), "percentage": round(over_exp_rate / raw_rejection_rate * 100, 1)},
        {"reason": "Poor Optical Focus", "count": int(round(rejected_images * (poor_focus_rate / raw_rejection_rate))), "percentage": round(poor_focus_rate / raw_rejection_rate * 100, 1)},
        {"reason": "Retina Not Centered (Fovea Missed)", "count": int(round(rejected_images * (uncentered_rate / raw_rejection_rate))), "percentage": round(uncentered_rate / raw_rejection_rate * 100, 1)},
        {"reason": "Low Sensor Resolution / Partial", "count": int(round(rejected_images * (low_res_rate / raw_rejection_rate))), "percentage": round(low_res_rate / raw_rejection_rate * 100, 1)},
    ]

    # Section 4: Rural Bandwidth Simulation
    # Time to upload 1 image over bw_mbps
    latency_sec = 0.08  # round trip ping delay
    upload_time_per_image = round((effective_img_mbit / bw_mbps) + latency_sec, 2)
    
    # 8-hour operating clinic day = 28,800 seconds
    clinic_day_seconds = 8 * 3600
    total_upload_data_mbit = accepted_images * effective_img_mbit
    available_bw_seconds = clinic_day_seconds
    total_possible_mbit = bw_mbps * available_bw_seconds
    bandwidth_utilization = min(100.0, round((total_upload_data_mbit / max(1.0, total_possible_mbit)) * 100.0, 1))

    # Network retries & dropped uploads on congested links
    retry_count = int(round(accepted_images * (0.01 + (0.12 if bw_mbps <= 2.0 else 0.02))))
    dropped_uploads = int(round(accepted_images * (0.005 if bw_mbps >= 5.0 else 0.025)))

    # Section 5: AI Server Throughput (Preprocessing + ResNet50 + Grad-CAM + Lesion Localization)
    # Standard single server CPU benchmark: Preprocessing=0.04s, ResNet50=0.08s, GradCAM=0.09s, LesionDet=0.11s -> Total ~0.32s
    single_image_ai_latency = 0.32  # seconds per image
    total_ai_capacity_ips = (1.0 / single_image_ai_latency) * ai_servers  # images per second
    daily_ai_processing_time = (accepted_images * single_image_ai_latency) / ai_servers
    ai_server_utilization = min(100.0, round((daily_ai_processing_time / clinic_day_seconds) * 100.0, 1))
    ai_queue_length = max(0, int(round((accepted_images / (clinic_day_seconds / single_image_ai_latency * ai_servers) - 1.0) * 15))) if ai_server_utilization > 95 else 0

    # Section 6: Doctor Review Queue
    # Clinical Prevalence: 
    # Class 0 (Normal): 65% (AI auto-discharges with healthy report)
    # Class 1 (Mild NPDR): 15% (AI 6-month reminder)
    # Class 2 (Moderate NPDR): 12% -> Referred to Doctor
    # Class 3 (Severe NPDR): 5% -> Urgent Doctor Referral
    # Class 4 (PDR): 3% -> Emergency Doctor Referral
    referral_rate = 0.20  # 20% of patients need ophthalmologist clinical sign-off
    patients_needing_review = int(round(patients_per_day * referral_rate))
    doctor_review_time_min = 4.0  # 4 minutes per referred case (inspecting heatmaps + lesion boxes)
    total_doctor_hours_needed = (patients_needing_review * doctor_review_time_min) / 60.0
    total_doctor_hours_available = doctors * 6.5  # 6.5 productive review hours per ophthalmologist
    doctor_utilization = min(100.0, round((total_doctor_hours_needed / max(0.1, total_doctor_hours_available)) * 100.0, 1))

    # Doctor queue & wait time
    if doctor_utilization > 90:
        waiting_time_hours = round(2.5 + ((doctor_utilization - 90) * 0.4), 1)
        doctor_queue_length = int(round(patients_needing_review * 0.45))
        backlog_cases = max(0, int(round(patients_needing_review - (total_doctor_hours_available * 60 / doctor_review_time_min))))
    else:
        waiting_time_hours = round(max(0.2, (doctor_utilization / 100.0) * 1.5), 1)
        doctor_queue_length = max(1, int(round(patients_needing_review * 0.12)))
        backlog_cases = 0

    # Section 7 & 8: District Capacity Estimation
    annual_patients_screened = patients_per_day * working_days
    diabetic_coverage_pct = min(100.0, round((annual_patients_screened / max(1, diabetic_pop)) * 100.0, 1))
    total_district_coverage_pct = round((annual_patients_screened / max(1, district_pop)) * 100.0, 2)
    days_to_complete_target = int(math.ceil(diabetic_pop / max(1, patients_per_day)))

    # Overall Pipeline Processing Latency
    avg_total_latency_sec = round(upload_time_per_image + single_image_ai_latency + 0.15, 2)

    # Section 10: Bottleneck Identification & Optimization Engine
    bottlenecks = []
    if bw_mbps <= 2.0:
        bottlenecks.append({"component": "Rural Bandwidth", "severity": "High", "impact": "Upload delays & transmission retries limit throughput."})
    if ai_server_utilization > 85.0:
        bottlenecks.append({"component": "AI Inference Servers", "severity": "Medium", "impact": "AI server cluster near peak saturation during surge camps."})
    if doctor_utilization > 85.0:
        bottlenecks.append({"component": "Ophthalmologist Review Queue", "severity": "Critical", "impact": "Doctor review backlog creates patient referral waiting delay."})
    if phcs * cameras < math.ceil(patients_per_day / 20):
        bottlenecks.append({"component": "Fundus Camera Hardware", "severity": "Medium", "impact": "Camera capacity limits patient acquisition velocity."})

    primary_bottleneck = bottlenecks[0]["component"] if bottlenecks else "System Well Balanced (No Critical Bottlenecks)"

    # Recommended Resources for Balanced Operation
    rec_phcs = max(phcs, int(math.ceil(patients_per_day / 25)))
    rec_ai_servers = max(2, int(math.ceil(patients_per_day * 2 * single_image_ai_latency / 18000)))
    rec_doctors = max(2, int(math.ceil((patients_per_day * 0.20 * doctor_review_time_min) / (6.0 * 60))))
    rec_bandwidth = "10 Mbps" if bw_mbps < 10 else f"{int(bw_mbps)} Mbps"

    optimization_summary = {
        "primary_bottleneck": primary_bottleneck,
        "bottlenecks": bottlenecks,
        "recommendations": {
            "phcs": rec_phcs,
            "ai_servers": rec_ai_servers,
            "doctors": rec_doctors,
            "bandwidth": rec_bandwidth,
            "estimated_daily_capacity": min(rec_phcs * 25, rec_doctors * 80),
            "estimated_annual_capacity": min(rec_phcs * 25, rec_doctors * 80) * working_days,
            "action_plan": f"Deploy {rec_ai_servers} AI inference nodes with {rec_bandwidth} uplink to support {rec_phcs} PHCs and {rec_doctors} reviewing ophthalmologists.",
        },
    }

    return {
        "config": config,
        "summary": {
            "patients_per_day": patients_per_day,
            "annual_patients_screened": annual_patients_screened,
            "diabetic_coverage_pct": diabetic_coverage_pct,
            "total_district_coverage_pct": total_district_coverage_pct,
            "days_to_complete_target": days_to_complete_target,
            "avg_processing_time_sec": avg_total_latency_sec,
        },
        "gateway": {
            "total_images_captured": total_images_captured,
            "accepted_images": accepted_images,
            "rejected_images": rejected_images,
            "rejection_rate_pct": round(rejection_rate * 100, 1),
            "acceptance_rate_pct": round((1.0 - rejection_rate) * 100, 1),
            "reasons": rejection_reasons,
        },
        "bandwidth": {
            "bandwidth_mbps": bw_mbps,
            "upload_time_per_image_sec": upload_time_per_image,
            "bandwidth_utilization_pct": bandwidth_utilization,
            "retry_count": retry_count,
            "dropped_uploads": dropped_uploads,
            "total_data_uploaded_mb": round((accepted_images * effective_img_mb), 1),
        },
        "ai_server": {
            "ai_servers": ai_servers,
            "images_per_sec": round(total_ai_capacity_ips, 1),
            "avg_ai_latency_sec": single_image_ai_latency,
            "inference_delay_sec": 0.08,
            "gradcam_delay_sec": 0.09,
            "lesion_delay_sec": 0.11,
            "preprocessing_delay_sec": 0.04,
            "server_utilization_pct": ai_server_utilization,
            "queue_length": ai_queue_length,
        },
        "doctor_queue": {
            "reviewing_doctors": doctors,
            "referred_patients": patients_needing_review,
            "referral_rate_pct": round(referral_rate * 100, 1),
            "doctor_utilization_pct": doctor_utilization,
            "queue_length": doctor_queue_length,
            "waiting_time_hours": waiting_time_hours,
            "backlog_cases": backlog_cases,
        },
        "kpis": [
            {
                "label": "Daily Patients Screened",
                "value": f"{patients_per_day}",
                "sub": f"{accepted_images} valid eye images",
                "status": "green" if patients_per_day >= 250 else "yellow",
            },
            {
                "label": "Gateway Acceptance",
                "value": f"{round((1.0 - rejection_rate) * 100, 1)}%",
                "sub": f"{rejected_images} recaptures guided",
                "status": "green" if rejection_rate < 0.18 else "yellow",
            },
            {
                "label": "Avg Pipeline Latency",
                "value": f"{avg_total_latency_sec}s",
                "sub": "Upload + AI + Grad-CAM",
                "status": "green" if avg_total_latency_sec < 4.0 else "yellow",
            },
            {
                "label": "AI Cluster Utilization",
                "value": f"{ai_server_utilization}%",
                "sub": f"{ai_servers} active AI nodes",
                "status": "green" if ai_server_utilization < 75 else ("yellow" if ai_server_utilization < 90 else "red"),
            },
            {
                "label": "Doctor Review Queue",
                "value": f"{doctor_queue_length} cases",
                "sub": f"{waiting_time_hours}h avg turnaround",
                "status": "green" if doctor_utilization < 75 else ("yellow" if doctor_utilization < 90 else "red"),
            },
            {
                "label": "Annual District Capacity",
                "value": f"{annual_patients_screened:,}",
                "sub": f"{diabetic_coverage_pct}% diabetic population",
                "status": "green" if diabetic_coverage_pct >= 80 else "yellow",
            },
        ],
        "optimization": optimization_summary,
    }
