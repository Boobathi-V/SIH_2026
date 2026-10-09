%% optimization.m
% SIH26038: Healthcare Resource Allocation & Bottleneck Optimization Engine
% Analyzes the telemedicine pipeline for saturation points and computes optimal
% allocations for PHCs, AI inference nodes, bandwidth tiers, and ophthalmologist rosters.

setup_dr_pipeline;

fprintf('\n>>> Running Telemedicine Resource Optimization Analysis...\n');

TargetPatientsPerDay = 333; % Target for 100k patients across 300 clinic days
MaxAllowedDoctorUtilization = 80.0; % Keep ophthalmologists under 80% burnout threshold
MaxAllowedAIUtilization = 75.0;     % Keep AI cluster under 75% peak load

% 1. Optimize Ophthalmologist Count
ReferredDailyCases = TargetPatientsPerDay * DoctorReferralRate;
HoursNeeded = (ReferredDailyCases * DoctorReviewTimeMin) / 60.0;
OptimalDoctors = ceil(HoursNeeded / (DoctorDailyHours * (MaxAllowedDoctorUtilization / 100)));

% 2. Optimize AI Inference Node Count
AcceptedDailyImages = TargetPatientsPerDay * ImagesPerPatient * (1 - TotalRejectionRate);
DailyAISeconds = AcceptedDailyImages * TotalAILatencySec;
OptimalAIServers = max(2, ceil(DailyAISeconds / (SimStopTime * (MaxAllowedAIUtilization / 100))));

% 3. Optimize PHC Network Distribution
OptimalPHCs = max(NumPHCs, ceil(TargetPatientsPerDay / 20));

% 4. Optimize Uplink Bandwidth Tier
if AvailableBandwidthMbps < 10.0
    RecommendedBandwidth = '10 Mbps (Fiber / LTE-A)';
else
    RecommendedBandwidth = sprintf('%.0f Mbps', AvailableBandwidthMbps);
end

% 5. Identify Critical Bottlenecks
Bottlenecks = {};
if AvailableBandwidthMbps <= 2.0
    Bottlenecks{end+1} = 'Bandwidth Constrained: Rural uplink limits image transmission throughput.';
end
if DoctorUtilizationPct > 85.0
    Bottlenecks{end+1} = 'Doctor Overload: Review backlog exceeds same-day clinical turnaround limits.';
end
if AIServerUtilizationPct > 80.0
    Bottlenecks{end+1} = 'AI Server Saturated: Inference nodes require horizontal scaling.';
end

if isempty(Bottlenecks)
    PrimaryBottleneck = 'None (Balanced Pipeline Infrastructure)';
else
    PrimaryBottleneck = Bottlenecks{1};
end

fprintf('\n=======================================================\n');
fprintf('  RESOURCE OPTIMIZATION & SCALING RECOMMENDATIONS       \n');
fprintf('=======================================================\n');
fprintf('  Target Screening Demand:     %d patients/day (100,000/year)\n', TargetPatientsPerDay);
fprintf('  Identified Bottleneck:       %s\n', PrimaryBottleneck);
fprintf('  Recommended PHCs:            %d centers\n', OptimalPHCs);
fprintf('  Recommended AI Nodes:        %d server nodes\n', OptimalAIServers);
fprintf('  Recommended Doctors:         %d reviewing ophthalmologists\n', OptimalDoctors);
fprintf('  Recommended Bandwidth:       %s\n', RecommendedBandwidth);
fprintf('  Optimal Daily Throughput:    %d patients/day\n', TargetPatientsPerDay);
fprintf('  Estimated Annual Capacity:   %d patients/year\n', TargetPatientsPerDay * TargetScreeningDays);
fprintf('=======================================================\n');
