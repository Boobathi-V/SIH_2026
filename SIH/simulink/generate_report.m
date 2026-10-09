%% generate_report.m
% SIH26038: Automated Report Generation for Simulink Pipeline Simulation
% Generates a formal text and data audit report summarizing feasibility metrics,
% healthcare resource optimization, and annual district screening capacity.

run_simulation;
optimization;

ReportFileName = 'simulink_screening_simulation_report.txt';
fid = fopen(ReportFileName, 'w');

if fid ~= -1
    fprintf(fid, '=======================================================================\n');
    fprintf(fid, '  SMART INDIA HACKATHON 2026 (SIH26038)\n');
    fprintf(fid, '  DISTRICT-LEVEL TELEMEDICINE DR SCREENING WORKFLOW SIMULATION REPORT\n');
    fprintf(fid, '=======================================================================\n\n');
    
    fprintf(fid, '1. DISTRICT HEALTHCARE DEMOGRAPHICS\n');
    fprintf(fid, '   Total District Population:       %d\n', DistrictPopulation);
    fprintf(fid, '   Estimated Diabetic Population:   %d (10%% Prevalence)\n', DiabeticPopulation);
    fprintf(fid, '   Operational Screening Days:      %d days/year\n', TargetScreeningDays);
    fprintf(fid, '   Target Screening Velocity:       %d patients/day\n\n', DailyArrivalTarget);
    
    fprintf(fid, '2. QUALITY REJECTION GATEWAY METRICS\n');
    fprintf(fid, '   Total Eye Captures:              %d images/day\n', TotalImages);
    fprintf(fid, '   Gradeable Images Passed:         %d (%.1f%%)\n', AcceptedImages, (1-TotalRejectionRate)*100);
    fprintf(fid, '   Substandard Captures Rejected:   %d (%.1f%%)\n', RejectedImages, TotalRejectionRate*100);
    fprintf(fid, '   Primary Rejection Factor:        Patient Motion Blur & Underexposure\n\n');
    
    fprintf(fid, '3. NETWORK & AI CLUSTER THROUGHPUT\n');
    fprintf(fid, '   Uplink Bandwidth:                %.1f Mbps\n', AvailableBandwidthMbps);
    fprintf(fid, '   Average Upload Delay:            %.2f s/image\n', AvgUploadTimeSec);
    fprintf(fid, '   AI Inference Cluster Size:       %d nodes\n', NumAIServers);
    fprintf(fid, '   AI Processing Throughput:        %.1f images/s\n', TotalAICapacityIPS);
    fprintf(fid, '   AI Cluster Utilization:          %.1f%%\n\n', AIServerUtilizationPct);
    
    fprintf(fid, '4. OPHTHALMOLOGIST REVIEW QUEUE & TURNAROUND\n');
    fprintf(fid, '   Cases Requiring Specialist:      %d patients/day (20%% Referral Rate)\n', ReferredPatients);
    fprintf(fid, '   Reviewing Ophthalmologists:      %d doctors\n', NumOphthalmologists);
    fprintf(fid, '   Doctor Workload Utilization:     %.1f%%\n', DoctorUtilizationPct);
    fprintf(fid, '   Active Review Queue Length:      %d cases\n', DoctorQueueLength);
    fprintf(fid, '   Average Report Turnaround:       %.1f hours\n\n', AvgWaitTimeHours);
    
    fprintf(fid, '5. ANNUALIZED DISTRICT CAPACITY & COVERAGE\n');
    fprintf(fid, '   Annual Screening Capacity:       %d patients/year\n', AnnualScreeningCapacity);
    fprintf(fid, '   Diabetic Population Covered:     %.1f%%\n', DiabeticPopulationCoveragePct);
    fprintf(fid, '   Identified Primary Bottleneck:   %s\n', PrimaryBottleneck);
    fprintf(fid, '   Recommended Balanced Doctors:    %d\n', OptimalDoctors);
    fprintf(fid, '   Recommended Balanced AI Nodes:   %d\n', OptimalAIServers);
    fprintf(fid, '=======================================================================\n');
    fclose(fid);
    fprintf('\n[SUCCESS] Simulation audit report written to: %s\n', ReportFileName);
else
    warning('Unable to create report file %s.', ReportFileName);
end
