input_data.folderpath = 'D:\Lab\Data\DLC_videos\Han_20201204_rwFreeReach\'; % DLC project folder
cd(input_data.folderpath)
dlc_file = dir('reconstructed-3d-data\*.csv');

dlc_file = dlc_file(2);

% load in dlc 3D data
marker_table = readtable([dlc_file.folder,filesep,dlc_file.name]);


%% remove points where any marker is not seen, remove pointX, pointY pointZ entries, is good frame, frame num

any_is_nan = any(isnan(table2array(marker_table)),2);

marker_table = marker_table(~any_is_nan,:);

remove_col_idx = [];
col_names = marker_table.Properties.VariableNames;

remove_col_idx(1) = find(~cellfun(@isempty,strfind(col_names,'is_good_frame')));
remove_col_idx(2) = find(~cellfun(@isempty,strfind(col_names,'fnum')));

remove_col_idx = [remove_col_idx, find(~cellfun(@isempty,strfind(col_names,'point')))];
remove_col_idx = [remove_col_idx, find(~cellfun(@isempty,strfind(col_names,'error')))];
remove_col_idx = [remove_col_idx, find(~cellfun(@isempty,strfind(col_names,'ncams')))];
remove_col_idx = [remove_col_idx, find(~cellfun(@isempty,strfind(col_names,'score')))];

marker_table(:,remove_col_idx) = [];

%% randomly drop a marker for someframes
num_drop = ceil(size(marker_table,2)*size(marker_table,1)*0.25);
idx_drop = datasample(1:1:size(marker_table,1),num_drop,'Replace',true);
num_markers = size(marker_table,2)/3;
idx_marker = datasample(1:1:num_markers,num_drop,'Replace',true);

marker_table_use = marker_table;
for i = 1:numel(idx_drop)
    % drop x,y,z data for the specified marker
    marker_table_use(idx_drop(i),3*(idx_marker(i)-1) + [1,2,3]) = {nan,nan,nan};
end

marker_data_true = table2array(marker_table);
marker_data_use = table2array(marker_table_use);

% remove cases where all data are missing
rem_idx = find(all(isnan(marker_data_use),2));
marker_data_true(rem_idx,:) = [];
marker_data_use(rem_idx,:) = [];

%% build ppca model with marker data

opt = statset('ppca'); opt.Display = 'iter'; opt.MaxIter = 100;
[coeff,score,pcavar,mu,v,S] = ppca(marker_data_use,15,'options',opt);

%% compare reconstructed data (in S) to actual data.

marker_data_true = marker_data_true'; marker_data_use = marker_data_use';
S.Recon = S.Recon';
nan_idx = find(isnan(marker_data_use));

err = marker_data_true(nan_idx) - S.Recon(nan_idx);

err = reshape(err,3,[])';
histogram(sqrt(sum(err.^2,2)))













