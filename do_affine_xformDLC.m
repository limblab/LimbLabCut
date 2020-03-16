function [ kinect_pos ] = do_affine_xformDLC( markersIn, affine_xform, plot_flag )

%Puts the kinect markers into handle coordinates

%Inputs:
%R - rotation matrix (to rotate the kinect positions)
%Tpre - translation of the kinect needed prior to rotation
%Tpost - translation of the kinect needed after rotation (to put back in
%handle coordinates)
%all_medians - the kinect marker locations in kinect coordinates

%Outputs:
%kinect_pos - the kinect marker locations in handle coordinates

%Note that the inputs plot_flag, times_good, pos_h, colors_xy, are all just
%used for making sure this works (via a plot). These can later be removed

%% Deal with number of inputs

if nargin<3 %The final parameters are only for plotting
    plot_flag=0;
end


%% Put all kinect positions in handle coordinates

%Rename kinect positions
all_medians_v2=markersIn;

%%X-coordinate of kinect is flipped: unflip it
all_medians_v2(:,1,:)=-all_medians_v2(:,1,:);

%Kinect is in meters, while handle is in cm
all_medians_v2=100*all_medians_v2;

%These are the matrices with the kinect positions in handle coordinates
kinect_pos=NaN(size(all_medians_v2(4:end, 3:end)));

%Loop through the markers. For every marker, multiply the shited kinect position
%by the affine matrix.
num_markers = 10;
for m=1:num_markers
    m_pos = markersIn(4:end, 3+3*(m-1):5+3*(m-1));
    %switch to homogenous coordinates
    m_pos_prime = affine_xform * [m_pos'; ones(1,size(m_pos',2))];
    %switch back to regular coordinates
    kinect_pos(:,3*(m-1)+1:3*(m-1)+3)=m_pos_prime(1:3,:)';
end

%Possibly flip z-coordinate (since the rotation doesn't know up from down)
%Based on where we put the kinect, the z-coordinate (in handle coordinates) of marker 8 should be positive. Flip z's otherwise.
temp=nanmean(kinect_pos(8,:,:),3);
if temp(3)<0
    kinect_pos(:,3,:)=-kinect_pos(:,3,:);
end

%% Another plot test

if plot_flag
    colors = {'g','b','r','y','g','g','b','r','g','r'};
    figure;
    for ctr = 1:10
        scatter3(kinect_pos(:,1 +(ctr-1)*3),kinect_pos(:,2 +(ctr-1)*3),kinect_pos(:,3 +(ctr-1)*3),[],colors{ctr});
        hold on
    end
%     axis equal
end

end

