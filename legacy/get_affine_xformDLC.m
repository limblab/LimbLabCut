function [ affine_xform, markersOut ] = get_affine_xformDLC( cds, kinect_times, md, x_lim_handle, y_lim_handle, plot_flag )

%This function finds the translation and rotation that are necessary for
%converting the kinect markers into handle coordinates

%Inputs:
%cds - cerebus file that contains handle information
%all_medians - kinect marker locations
%x_lim_handle, y_lim_handle - locations of handle to consider
%plot_flag - whether to plot the results

%Outputs:
% affine transformation matrix

%Note that the output times_good, pos_h, colors_xy, are all just
%used for making sure this works (via a plot). These can later be removed

%% 4a. Get handle information
handle_pos = [cds.kin.x cds.kin.y];
handle_times = cds.kin.t; %This should be the same as analog_ts

%% Get the handle times that correspond to the kinect times

%Note that there is a faster, but more complicated, way of doing this in the
%squarewave aligning function. Time isn't an issue here, so I haven't
%changed it.

% 
% handle_time_idxs=zeros(length(n_times),1); %Initialize the handle time indexes
% %For each kinect time, find the closest handle time. handle_time_idxs has
% %the indexes of all the corresponding handle times.
% for i=1:n_times
%     [~,handle_time_idxs(i)]=min(abs(handle_times-kinect_times(i)));
% end
% 
% handle_times_ds=handle_times(handle_time_idxs); %These are the handle times that correspond to all the kinect times
% handle_pos_ds=handle_pos(handle_time_idxs,:); %The handle positions at all the kinect times

handle_pos_ds = interp1(handle_times,handle_pos,kinect_times);
handle_pos_ds  = handle_pos_ds;

%% Find time points that we need to remove (for several reasons)
% kinect_times = kinect_times(kinect_times>=0);
%Remove kinect times from when the handle wasn't recorded

kin_pos= md(1:end,end-2:end)'; %Positions of the above hand points (recorded by the kinect)
marker_pos = md(1:end,:);
%Remove kinect times from when the hand is missing
missing=isnan(kin_pos(1,:)); %Times when hand points are missing

missing_smooth=smooth(single(missing),10); %Smooth when hand points are missing to find time areas when almost all hand points are there

%Find the good times that we should use for the alignment. Good times are
%those that:
%1. The hand is not missing
%2. The hand is not missing a lot around the time point (it's missing <20%
%of the time in the surrounding 10 frames)
%3. The handle was recorded (~kin_early & ~kin_late)
%4. The handle positions is within the specified limits
times_good=~missing' & missing_smooth<.2 & ...
     handle_pos_ds(:,1)>x_lim_handle(1) & handle_pos_ds(:,1)<x_lim_handle(2) & handle_pos_ds(:,2)>y_lim_handle(1) & handle_pos_ds(:,2)<y_lim_handle(2);

%Get times and positions for the kinect and handle to be compared
kin_pos_good=kin_pos(:,times_good);
handle_pos_ds_good=handle_pos_ds(times_good,:);

%% Align

%Rename for simplicity
pos_k=kin_pos_good';
pos_h=handle_pos_ds_good;
pos_h(:,3)=0; %Set z-coordinate as 0 for handle

%X-coordinate of kinect is flipped: unflip it
pos_k(:,1)=-pos_k(:,1);

%Kinect is in meters, while handle is in cm: put everything in cm
pos_k=pos_k*100;

%Find the rotation with Kabsch algorithm
[U,r,lrms] = Kabsch(pos_k',pos_h');

disp(['The rms for aligning kinect hand position to handle is ' num2str(lrms) ' cm'])

%compute affine transform
affine_xform = [U r; 0 0 0 1];

%% Apply
pos_k_affine = [pos_k ones(size(pos_k,1),1)] * affine_xform';
% pos_k_affine = pos_k * affine_xform(1:3,1:3)';
% pos_k_affine = pos_k;
% pos_h_affine = [pos_h ones(size(pos_h,1),1)] / affine_xform';
num_markers = 8;
for i = 1:num_markers
    temp =[marker_pos(:, 3+3*(i-1):5+3*(i-1)), ones(length(marker_pos(:,1)),1)];
    temp(:,1) = -1*temp(:,1);
    temp(:,1:3) = temp(:,1:3).*100;
    temp = temp*affine_xform';
    temp(:,3) = -1*temp(:,3);

    markersOut(:,1+3*(i-1):3+3*(i-1)) = temp(:,1:3);
end

%% Plot to make sure it worked

if plot_flag
    
    %Make color map
    xVal=(pos_h(:,1)-min(pos_h(:,1)))/max(pos_h(:,1)-min(pos_h(:,1)));
    yVal=(pos_h(:,2)-min(pos_h(:,2)))/max(pos_h(:,2)-min(pos_h(:,2)));
    colors_xy = [.6*ones(size(xVal)),xVal,yVal];
    
    %Plot the kinect points that have been rotated (with coloring based on where
    %the handles initially were)
    figure; scatter3(pos_k_affine(:,1),pos_k_affine(:,2),pos_k_affine(:,3),[],colors_xy,'fill')
    title('Kinect')
    axis equal
%     xlim(x_lim_handle);
%     ylim(y_lim_handle);
%     zlim([-15 15]);
    
    %Plot the handle points
    figure; scatter3(pos_h(:,1),pos_h(:,2),pos_h(:,3),[],colors_xy,'fill')
%     figure; scatter3(pos_h_affine(:,1),pos_h_affine(:,2),pos_h_affine(:,3),[],colors_xy,'fill')
    title('Handle')
    axis equal
    
    colors = {'r', 'b', 'g', 'k', 'r', 'b', 'g', 'k', 'r', 'b'};
    figure;
    hold on
    for i = 1:num_markers
        temp = markersOut(:, 1+3*(i-1):3+3*(i-1));
        scatter3(temp(:,1), temp(:,2), temp(:,3),[], colors{i})
    end
end

end

