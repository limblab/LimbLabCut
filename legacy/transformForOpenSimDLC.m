%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% function [md_opensim] = transformForOpenSim(marker_data)
%
%   This function transforms marker data from lab coordinates into OpenSim
%   coordinates. This function is to be used in getTRCfromMarkers.
%
% INPUTS:
%   marker_data  : struct containing marker data, in robot coordinates
%       Fields:
%           pos - position of markers, aligned spatially to match handle
%           movement
%           t - times for video frames of marker capture, aligned to
%           cerebus collection
%   cds : CDS file to extract handle kinematics from
%
% OUTPUTS:
%   md_opensim : struct of marker_data in OpenSim coordinates
%       Fields:
%           pos - position of markers, aligned to OpenSim coordinates
%           t - times for video frames of marker capture, aligned to
%           cerebus collection
%   handle_opensim : position of the handle in OpenSim coordinates
%
%
% Written by Raeed Chowdhury and Joshua Glaser. Updated April 2017.
%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function [md_opensim,handle_opensim] = transformForOpenSimDLC(marker_data,cds)
% Robot coordinates:
% Origin at shoulder joint center of robot, x is to right, y is towards screen, z is up
% OpenSim coordinates:
% Origin at shoulder joint center (marker 9), x is towards screen, y is up, z is to right


md_opensim = marker_data;

% change from cm to meters
md_opensim.pos = md_opensim.pos/100;


% do same for handle position
handle_pos = [cds.kin.x cds.kin.y zeros(height(cds.kin),1)];
handle_pos=interp1(cds.kin.t,handle_pos,marker_data.t);
recenter_handle = handle_pos;
handle_opensim =  recenter_handle(:,[2 3 1])/100;
num_markers = 8;
colors = {'r', 'b', 'g', 'k', 'r', 'b', 'g', 'k', 'r', 'b'};
figure;
hold on
sC = md_opensim.pos(:,1:3);
 
for i = 1:num_markers
    temp = md_opensim.pos(:,1+(i-1)*3: 3+(i-1)*3) - sC;
    temp = temp(:,[2,3,1]);
    scatter3(temp(:,1), temp(:,2), temp(:,3),[], colors{i})

    md_opensim.pos(:,1+(i-1)*3: 3+(i-1)*3) = temp;
    
end
xlabel('x')
ylabel('Y')
zlabel('z')
a = 1;
end
