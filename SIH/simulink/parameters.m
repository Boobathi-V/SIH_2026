%% Parameters for Diabetic Retinopathy Telemedicine Screening Simulation
% SIH26038: District-Level Telemedicine Screening Pipeline Simulation
% Models healthcare resource allocation, bandwidth constraints, AI server throughput,
% rejection gateway statistics, ophthalmologist review queues, and annual district capacity.

%% District Demographics
DistrictPopulation = 1000000;         % Total population in target district
DiabeticPrevalence = 0.10;            % 10% diabetic prevalence
DiabeticPopulation = DistrictPopulation * DiabeticPrevalence; % 100,000 diabetic citizens
TargetScreeningDays = 300;            % Annual working days for rural PHCs
DailyPatientTarget = 333;             % Required daily arrivals to cover population (100k/300)

%% Rural Healthcare Infrastructure
NumPHCs = 25;                         % Primary Health Centers connected to network
CamerasPerPHC = 2;                    % Non-mydriatic fundus cameras per PHC
TechniciansPerPHC = 2;                % Certified screening health workers per PHC
HoursPerClinicDay = 8;                % Operating hours per day (28,800 seconds)

%% Image Acquisition & Quality Rejection Gateway
ImagesPerPatient = 2;                 % Both eyes (macula-centered & disc-centered)
ImageRawSizeMB = 3.2;                 % High-resolution fundus image size
CompressionRatio = 0.35;              % JPEG 85 lossless-perceptual compression
EffectiveImageSizeMB = ImageRawSizeMB * CompressionRatio; % ~1.12 MB
EffectiveImageSizeMbit = EffectiveImageSizeMB * 8;         % ~8.96 Mbit

% Historical quality rejection probabilities at community level
BlurRejectionRate = 0.05;             % Motion blur / patient blink
LowIlluminationRate = 0.04;           % Small pupil / underexposure
OverExposureRate = 0.02;              % Cornea flash reflection
PoorFocusRate = 0.03;                 % Operator optical focus error
UncenteredRetinaRate = 0.02;          % Macula/fovea out of frame
LowResolutionRate = 0.01;             % Hardware sensor fault
TotalRejectionRate = BlurRejectionRate + LowIlluminationRate + OverExposureRate + ...
                     PoorFocusRate + UncenteredRetinaRate + LowResolutionRate; % ~17%

%% Telemedicine Bandwidth Constraints
AvailableBandwidthMbps = 10.0;        % PHC 4G/fiber uplink bandwidth
NetworkLatencySec = 0.080;            % Round-trip transmission ping latency
UploadTimePerImageSec = (EffectiveImageSizeMbit / AvailableBandwidthMbps) + NetworkLatencySec;

%% AI Screening Server Cluster
NumAIServers = 3;                     % Parallel GPU/CPU inference server nodes
PreprocessingLatencySec = 0.040;      % Circular FOV crop, LAB CLAHE enhancement
InferenceLatencySec = 0.080;          % ResNet-50 / EfficientNet forward pass
GradCAMLatencySec = 0.090;            % Target layer gradient backprop & heatmap overlay
LesionDetectionLatencySec = 0.110;    % Vessel segmentation + Microaneurysm/Exudate extraction
TotalAILatencySec = PreprocessingLatencySec + InferenceLatencySec + ...
                    GradCAMLatencySec + LesionDetectionLatencySec; % ~0.32s per image

%% Clinical Referral & Doctor Review Queue
NormalDischargeRate = 0.65;           % Class 0: No DR -> Auto-discharged with healthy report
MildFollowUpRate = 0.15;              % Class 1: Mild DR -> Auto 6-month reminder
DoctorReferralRate = 0.20;            % Class 2/3/4 -> Referred to Ophthalmologist
NumOphthalmologists = 5;              % Tele-triage eye doctors on duty
DoctorReviewTimeMin = 4.0;            % Minutes spent reviewing lesion heatmaps & patient history
DoctorDailyHours = 6.5;               % Effective review hours per doctor per day

disp('SIH26038: Simulink parameters initialized successfully.');
