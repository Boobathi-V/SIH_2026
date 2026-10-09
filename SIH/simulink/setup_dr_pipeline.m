%% setup_dr_pipeline.m
% SIH26038: Setup Script for Diabetic Retinopathy Telemedicine Simulink Pipeline
% Prepares the workspace, validates dependencies, loads baseline parameters,
% and configures the Stateflow and SimEvents / Discrete-Event runtime variables.

clear;
clc;

fprintf('=======================================================\n');
fprintf('  SIH26038: Diabetic Retinopathy Telemedicine Pipeline \n');
fprintf('  Simulink Workflow & Resource Allocation Simulation    \n');
fprintf('=======================================================\n\n');

% 1. Load Parameters
if exist('parameters.m', 'file') == 2
    parameters;
    fprintf('[OK] Baseline simulation parameters loaded.\n');
else
    error('parameters.m not found. Please ensure all simulation scripts are in the working directory.');
end

% 2. Setup Simulation Time Horizon
% Simulating an 8-hour rural clinic day (in seconds)
SimStopTime = HoursPerClinicDay * 3600; % 28,800 seconds
SampleTime = 1.0; % 1-second discrete event step

% 3. Calculate Poisson Arrival Mean Inter-Arrival Time
DailyArrivalTarget = DailyPatientTarget;
MeanInterArrivalTimeSec = SimStopTime / DailyArrivalTarget;
fprintf('[OK] Mean Patient Inter-Arrival Time: %.2f seconds\n', MeanInterArrivalTimeSec);

% 4. Verify Model Initialization
ModelName = 'DR_Screening_Pipeline';
fprintf('[READY] Model "%s" workspace configured. Ready to run "run_simulation.m".\n', ModelName);
