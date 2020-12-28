%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% function [kinect_times] = realignMarkerTimes(cerebus_vals,marker_data,plot_flag)
%
%   This function realigns the data collected by the kinect to the data
%   taken by the Cerebus system. This function is meant to be used in
%   realignMarkerSpacetime.
%
% INPUTS:
%   cerebus_vals : the analog cell from CDS containing KinectSyncPulse
%   marker_data  : struct containing marker data, drawn directly from the
%   color tracking script
%   plot_flag    : flag for whether to plot final alignment
%
% OUTPUTS:
%   kinect_times : vector of realigned times for marker data
%
%
% Written by Raeed Chowdhury and Joshua Glaser. Updated April 2017.
%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function timesOut = realignMarkerTimesDLC(cerebus_vals,marker_data,plot_flag)

frames =marker_data(:,1);
frames(isnan(frames)) = [];
times = marker_data(:,2);
times(isnan(times)) = [];
times = times(times>=0);


start_cer= cerebus_vals.t(find(cerebus_vals.SyncPulse>500,1));
end_cer = cerebus_vals.t(find(cerebus_vals.SyncPulse>500, 1,'last'));

durCer = end_cer- start_cer;
durCam = times(end);

framesCer = length(find(diff(cerebus_vals.SyncPulse)>500));
framesCam = length(frames);

if framesCer ~= framesCam
    warning('Mismatched frame counts between cerebus and DLC')
end

time = times + start_cer;
% tPlot = .001:.001:max(time);
% onPlot = zeros(length(tPlot),1);
% onPlot(floor(time*1000)) = 1;
% 
% sum(diff(cerebus_vals.SyncPulse)>500);
% 
% figure
% plot(tPlot+start_cer, onPlot)
% yyaxis right
% plot(cerebus_vals.t, cerebus_vals.SyncPulse)
%% 3c. Align kinect led values with cerebus squarewave
timesOut  = time;