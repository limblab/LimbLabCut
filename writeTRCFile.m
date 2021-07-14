function [  ] = writeTRCFile( md_opensim,fname )
    % write a trc file from a dlc video file (see make_reaching_td)

    % first initialise the header with a column for the Frame # and the Time
    % also initialise the format for the columns of data to be written to file
    dataheader1 = 'Frame#\tTime\t';
    dataheader2 = '\t\t';
    format_text = '%i\t%2.4f\t';
    % initialise the matrix that contains the data as a frame number and time row
    nframe = size(md_opensim,1);
    
    data_out = [1:1:nframe; md_opensim.t'];

    nmarkers = (size(md_opensim,2)-1)/3; % don't count time field
    markers = md_opensim.Properties.VariableNames(1:3:end);
    keep_mask = ~strcmpi(markers,'t');
    
    % rename markers to match opensim names. NOTE: the opensim names should
    % be changed in the future, but I (Joseph) don't want to mess with too
    % many things at once
    % shoulder->Shoulder_JC; elbow1->Pronation_Pt1; elbow2->Marker_6;
    % wrist1->Marker_4; wrist2->Marker_5; hand1->Marker_2; hand2->Marker_1
    % hand3->Marker_3
    for i_m = 1:numel(markers)
        switch(markers{i_m})
            case 'shoulder_x'
                markers{i_m} = 'Shoulder_JC';
            case 'shoulder1_x'
                markers{i_m} = 'Shoulder_JC';
            case 'elbow1_x'
                markers{i_m} = 'Pronation_Pt1';
            case 'elbow2_x'
                markers{i_m} = 'Marker_6';
            case 'wrist1_x'
                markers{i_m} = 'Marker_4';
            case 'wrist2_x'
                markers{i_m} = 'Marker_5';
            case 'hand1_x'
                markers{i_m} = 'Marker_2';
            case 'hand2_x'
                markers{i_m} = 'Marker_1';
            case 'hand3_x'
                markers{i_m} = 'Marker_3';
            otherwise
                keep_mask(i_m) = 0;
        end
    end
    
    markers = markers(keep_mask==1);
    nmarkers = numel(markers);
    
    
    
    % now loop through each maker name and make marker name with 3 tabs for the
    % first line and the X Y Z columns with the marker number on the second
    % line all separated by tab delimeters
    % each of the data columns (3 per marker) will be in floating format with a
    % tab delimiter - also add to the data matrix
    for i = 1:nmarkers
        dataheader1 = [dataheader1 markers{i} '\t\t\t'];    
        dataheader2 = [dataheader2 'X' num2str(i) '\t' 'Y' num2str(i) '\t'...
            'Z' num2str(i) '\t'];
        format_text = [format_text '%f\t%f\t%f\t'];
        % add 3 rows of data for the X Y Z coordinates of the current marker
        % first check for NaN's and fill with a linear interpolant - warn the
        % user of the gaps
        clear m
        marker_idx = [1,2,3] + (i-1)*3;
        m = find(isnan(md_opensim{:,marker_idx(1)}));
        if ~isempty(m)
            clear t d
            disp(['Warning -' markers{i} ' data missing in parts. Linear interpolation to fill gaps'])
            t = md_opensim.t';
            t(m) = [];
            d = md_opensim{:,marker_idx};
            d(m,:) = [];
            md_opensim{:,marker_idx} = interp1(t,d,md_opensim.t,'linear','extrap');
        end
        data_out = [data_out; md_opensim{:,marker_idx}'];
    end
    dataheader1 = [dataheader1 '\n'];
    dataheader2 = [dataheader2 '\n'];
    format_text = [format_text '\n'];

    disp('Writing trc file...') 

    %Output marker data to an OpenSim TRC file


    %open the file
    fid_1 = fopen(fname,'w');

    % compute frequency, nrows, nmarkers, set units, freq again, start and
    % end frame nums
    freq = 1./mean(diff(md_opensim.t));
    
    % first write the header data
    fprintf(fid_1,'PathFileType\t4\t(X/Y/Z)\t %s\n',fname);
    fprintf(fid_1,'DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\tOrigDataRate\tOrigDataStartFrame\tOrigNumFrames\n');
    fprintf(fid_1,'%d\t%d\t%d\t%d\t%s\t%d\t%d\t%d\n', freq, freq, size(md_opensim,1), nmarkers, 'm', freq,1,size(md_opensim,2)); 
    fprintf(fid_1, dataheader1);
    fprintf(fid_1, dataheader2);

    % then write the output marker data
    fprintf(fid_1, format_text,data_out);

    % close the file
    fclose(fid_1);

    disp('Done.')


end

