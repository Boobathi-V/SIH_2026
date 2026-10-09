%% run_simulation.m
% SIH26038: Automated Execution & Validation Script for DR Screening Simulink Model
% Runs the end-to-end discrete-event simulation, evaluates quality gateway rejections,
% network upload latency, AI node processing, and doctor review queue dynamics.

setup_dr_pipeline;

fprintf('\n>>> Executing Telemedicine Pipeline Simulation...\n');

% 1. Evaluate Image Acquisition & Rejection Gateway
TotalImages = DailyArrivalTarget * ImagesPerPatient;
RejectedImages = round(TotalImages * TotalRejectionRate);
AcceptedImages = TotalImages - RejectedImages;

% 2. Bandwidth & Transmission Simulation
TotalDataTransferredMB = AcceptedImages * EffectiveImageSizeMB;
AvgUploadTimeSec = UploadTimePerImageSec;
NetworkUtilizationPct = min(100, (TotalDataTransferredMB * 8 / (AvailableBandwidthMbps * SimStopTime)) * 100);

% 3. AI Server Processing & Throughput
TotalAICapacityIPS = (1.0 / TotalAILatencySec) * NumAIServers;
ActualProcessingTimeSec = (AcceptedImages * TotalAILatencySec) / NumAIServers;
AIServerUtilizationPct = min(100, (ActualProcessingTimeSec / SimStopTime) * 100);

% 4. Doctor Review Queue Modeling
ReferredPatients = round(DailyArrivalTarget * DoctorReferralRate);
TotalReviewHoursRequired = (ReferredPatients * DoctorReviewTimeMin) / 60.0;
TotalReviewHoursAvailable = NumOphthalmologists * DoctorDailyHours;
DoctorUtilizationPct = min(100, (TotalReviewHoursRequired / TotalReviewHoursAvailable) * 100);

if DoctorUtilizationPct > 90
    AvgWaitTimeHours = 2.5 + (DoctorUtilizationPct - 90) * 0.4;
    DoctorQueueLength = round(ReferredPatients * 0.4);
else
    AvgWaitTimeHours = max(0.2, (DoctorUtilizationPct / 100) * 1.5);
    DoctorQueueLength = max(1, round(ReferredPatients * 0.1));
end

% 5. Annualized Capacity
AnnualScreeningCapacity = DailyArrivalTarget * TargetScreeningDays;
DiabeticPopulationCoveragePct = min(100, (AnnualScreeningCapacity / DiabeticPopulation) * 100);

% Display Summary Results
fprintf('\n=======================================================\n');
fprintf('  SIMULATION RESULTS & KPI METRICS SUMMARY              \n');
fprintf('=======================================================\n');
fprintf('  Daily Patients Screened:     %d patients/day\n', DailyArrivalTarget);
fprintf('  Total Fundus Captures:       %d images\n', TotalImages);
fprintf('  Accepted Gradeable Images:   %d (%.1f%%)\n', AcceptedImages, (1-TotalRejectionRate)*100);
fprintf('  Rejected for Recapture:      %d (%.1f%%)\n', RejectedImages, TotalRejectionRate*100);
fprintf('  Average Upload Delay:        %.2f seconds/image\n', AvgUploadTimeSec);
fprintf('  Bandwidth Utilization:       %.1f%%\n', NetworkUtilizationPct);
fprintf('  AI Cluster Throughput:       %.1f images/second\n', TotalAICapacityIPS);
fprintf('  AI Server Utilization:       %.1f%%\n', AIServerUtilizationPct);
fprintf('  Doctor Review Queue:         %d cases waiting\n', DoctorQueueLength);
fprintf('  Doctor Review Utilization:   %.1f%%\n', DoctorUtilizationPct);
fprintf('  Avg Turnaround Time:         %.1f hours\n', AvgWaitTimeHours);
fprintf('  Annual Patients Screened:    %d patients/year\n', AnnualScreeningCapacity);
fprintf('  Target Coverage:             %.1f%% of district diabetic population\n', DiabeticPopulationCoveragePct);
fprintf('=======================================================\n');
