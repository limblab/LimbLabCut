% get image timestamps for a set of videos, compare time stamps, dropout
% rate, dropout times, etc.


video_folder = 'D:\Lab\Data\DLC_videos\Crackle_20201202\';
video_list = dir([video_folder,'*.avi.xiinfo*']);


%%
vid_idx = 4;
fid = fopen([video_list(vid_idx).folder,filesep,video_list(vid_idx).name]);

first_frame_val = -1;

tline = fgetl(fid);
timestamps = [];
while ischar(tline)
    % check if timestamp data
    is_timestamp = ~isempty(strfind(tline,'timestamp'));
    
    if(is_timestamp)
        % number is between two quotes
        quote_idx = strfind(tline,'"');
        timestamp_temp = str2num(tline(quote_idx(1)+1:quote_idx(2)-1));
        if(first_frame_val < 0 && timestamp_temp > 0)
            first_frame_val = timestamp_temp;
        end
        
        if(timestamp_temp > 0)
            timestamps(end+1) = timestamp_temp-first_frame_val;
        end
    end
    
    tline = fgetl(fid);
end


fclose(fid);

% histogram(diff(timestamps))