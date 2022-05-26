# -*- coding: utf-8 -*-
"""
Created on Tue Apr  5 16:12:39 2022

@author: Joseph Sombeck
"""

#%%
import pandas as pd
import numpy as np
from scipy.spatial.transform import Rotation as R
import glob
import matplotlib.pyplot as plt

from pathlib import Path
#%% make a shorter file because opensim is slow
fname = r'D:\Lab\Data\DLCgrasp_training_frames\data3Dlong.csv'
jarv = pd.read_csv(fname,header=[0,1])

jarv = jarv.iloc[np.arange(0,jarv.shape[0],50),:]
jarv.reset_index()
new_fname = r'D:\Lab\Data\DLCgrasp_training_frames\data3Dshort.csv'
fpath = Path(new_fname)
fpath.parent.mkdir(parents=True, exist_ok=True)

jarv.to_csv(fpath,index=False)
#%% load in jarvis file

fname = r'D:\Lab\Data\DLCgrasp_training_frames\data3Dshort.csv'
jarv = pd.read_csv(fname,header=[0,1])
hand = 'L'



# convert column names to those required by the opensim model
# this dictionary takes our name and outputs opensims name
name_conv_dict = {'Index_T' : 'D2D',
                  'Index_D' : 'D2I',
                  'Index_M' : 'D2P',
                  'Middle_T' : 'D3D',
                  'Middle_D' : 'D3I',
                  'Middle_M' : 'D3P',
                  'Ring_M' : 'D4P',
                  'Ring_D' : 'D4I',
                  'Ring_T' : 'D4D',
                  'Pinky_M' : 'D5P',
                  'Pinky_D' : 'D5I',
                  'Pinky_T' : 'D5D',
                  'Thumb_D' : 'D1P',
                  'Thumb_T' : 'D1D',
                  'Thumb_M' : 'D1H',
                  'Index_P' : 'D2H',
                  'Middle_P' : 'D3H',
                  'Ring_P' : 'D4H',
                  'Pinky_P' : 'D5H',
                  'Palm' : 'HC',
                  'Wrist_U' : 'HL',
                  'Wrist_R' : 'HM'}

open_data = jarv.rename(mapper=name_conv_dict,level=0,axis=1)

# this dropping works, but doesn't update the internal column names for some reason. This is super annoying
open_data.drop(('Thumb_P','x'),axis=1,inplace=True)
open_data.drop(('Thumb_P','y'),axis=1,inplace=True)
open_data.drop(('Thumb_P','z'),axis=1,inplace=True)


# recenter all markers on palm
# rotate axes... DLc/Jarvis -> ncams = 
# ncames -> opensim = x->z, y->-y, z->x
# full rotation -> x->-y, y->z, z->-x
zero_data = open_data['HC']
marker_names = []

for i in open_data.columns.levels[0]:
    if(i != 'Thumb_P'):
        temp_data = open_data[i] - zero_data
        
        
        # do the conversion in two steps to avoid bugs....
        # DLC/Jarvis -> ncams: x->y, y->x, z->-z
        copy_data = temp_data.copy()
        temp_data['x'] = copy_data['y']
        temp_data['y'] = copy_data['x']
        temp_data['z'] = -copy_data['z']
        
        # ncams ->opensim: x->z, y->-y, z->x
        copy_data = temp_data.copy()
        temp_data['x'] = copy_data['z']
        temp_data['y'] = -copy_data['y']
        temp_data['z'] = copy_data['x']
        
        # full rotation: x->-z, y->-x, z->y ??
        
        
        # I think the below is wrong...
        #full rotation -> x->-y, y->z, z->-x
        #copy_data = temp_data.copy()
        #temp_data['x'] = -copy_data['y']
        #temp_data['y'] = copy_data['z']
        #temp_data['z'] = -copy_data['x']
        
        
        open_data[i] = temp_data 
        marker_names.append(i)
        

#%% write trc file....

trc_fname = fname[:-4] + '.trc'
frame_rate = 30; # Hz

# first initialise the header with a column for the Frame # and the Time
# also initialise the format for the columns of data to be written to file
dataheader1 = 'Frame#\tTime\t';
dataheader2 = '\t\t';
format_text = '%i\t%2.4f\t';

# initialise the matrix that contains the data as a frame number and time row
data_out = open_data.to_numpy()

data_out = data_out/1000 # convert from mm to m

nframes = data_out.shape[0]
nmarkers = int(data_out.shape[1]/3)

idx_list = np.arange(1,data_out.shape[0]+1,1).reshape((-1,1))
time_list = idx_list/frame_rate

data_out = np.concatenate((idx_list, time_list,data_out),axis=1)

# fill nans with a constant for now
data_out = np.nan_to_num(data_out)

# now loop through each maker name and make marker name with 3 tabs for the
# first line and the X Y Z columns with the marker number on the second
# line all separated by tab delimeters
# each of the data columns (3 per marker) will be in floating format with a
# tab delimiter - also add to the data matrix
for i in range(1,nmarkers+1):
    dataheader1 = dataheader1 + marker_names[i-1] + '\t\t\t';    
    dataheader2 = dataheader2 + 'X' + str(i) + '\t' + 'Y' + str(i) + '\t' + 'Z' + str(i) + '\t'
    format_text = format_text + '%f\t%f\t%f\t'
    


dataheader1 = dataheader1 + '\n'
dataheader2 = dataheader2 + '\n'
format_text = format_text + '\n'

print('writing the file....')


#Output marker data to an OpenSim TRC file
#open the file

with open(trc_fname,'w') as f:
    
    # compute frequency, nrows, nmarkers, set units, freq again, start and
    # end frame nums
    
    # first write the header data
    f.write('PathFileType\t4\t(X/Y/Z)\t' + trc_fname + '\n')
    f.write('DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\tOrigDataRate\tOrigDataStartFrame\tOrigNumFrames\n')
    f.write(str(frame_rate) + '\t' + str(frame_rate) + '\t' + str(nframes) + '\t' + str(nmarkers) + '\t' + 'm' + '\t' +str(frame_rate) + '\t1\t' + str(nframes) + '\n')
    f.write(dataheader1)
    f.write(dataheader2)

    # then write the output marker data
    for i in range(data_out.shape[0]):
        f.write(format_text % tuple(data_out[i]))


print('Done.')

#%% load in marker positions from open sim, compare to original

analysis_fol = r'D:\Lab\Data\DLCgrasp_training_frames\Analysis'

# find '*BodyKinematics_pos*.sto' in analysis fname
analysis_fname = glob.glob(analysis_fol + '\\*BodyKinematics_pos*.sto')[0]
os_df = pd.read_csv(analysis_fname,header=13,delimiter='\t')


# set marker -> body name dictionary

marker_body_dict = {}
marker_fname = r'D:\Lab\GIT\ms_arm_and_hand\AAH Model\LeftArmAndHand_Markers.xml'

with open(marker_fname, 'r') as f:
    lines = f.readlines()

# all markers are built the same: look for 'Marker name=', chars within " " will be marker name
# then, two lines later will be body (<body>BODY</body>)
    
curr_mark = ''
curr_body = ''
for l in lines:
    if(l.find('Marker name=') != -1):
        quote_idx_1 = l.find('\"')
        quote_idx_2 = l.find('\"',quote_idx_1+1)
        curr_mark = l[quote_idx_1 + 1:quote_idx_2]
        
    if(l.find('<body>') != -1):
        idx_1 = l.find('<body>')
        idx_2 = l.find('</body>')
        curr_body = l[idx_1 + 6:idx_2]
        
        marker_body_dict[curr_mark] = curr_body
    # when we reach a body, append curr_mark and curr_body to dictionary



#%% compare body positions to original markers ..... which aren't actually the same 
jarv_data = open_data/1000 # change name since this is confusing...
# first get zero position based on palm
os_palm_name = marker_body_dict[name_conv_dict['Palm']]

zero_data = np.zeros((os_df.shape[0],3))

for cname in os_df.columns:
    if(os_palm_name in cname and '_O' not in cname): # remove orientation data
        if('_X' in cname):
            zero_data[:,0] = os_df[cname]
        if('_Y' in cname):
            zero_data[:,1] = os_df[cname]
        if('_Z' in cname):
            zero_data[:,2] = os_df[cname]



# get truncated data matrix of only x,y,z data
keep_names = []
for os_cname in os_df.columns:
    for jarv_cname in jarv_data.columns.levels[0]:
        if(jarv_cname in marker_body_dict and marker_body_dict[jarv_cname] in os_cname and '_O' not in os_cname and '_P' not in os_cname): # remove orientation and PHANT, whatever that is
            keep_names.append(os_cname)

            

os_df = os_df[keep_names]


#%% compare opens sim and jarvis for each marker

# for each column in jarv_data, find corresponding column in os_df
test_cols = jarv_data.columns[0:20]
for jname in test_cols:
    # find marker_body_dict[jname[0]]
    data_j = jarv_data[jname]
    for os_name in os_df.columns:
        if(marker_body_dict[jname[0]] in os_name and jname[1].upper() == os_name[-1]):
            data_os = os_df[os_name]
            
    # compare data_j and data_os...start by plotting
    plt.figure()
    plt.plot(data_j,data_os,'.')
    plt.title(jname)






#%% get distances between markers....
marker_names = ['D2I', 'D2P']
axis_names = ['_X', '_Y', '_Z']


dist = []
for a in axis_names:
    dist_temp = np.square(os_df[marker_body_dict[marker_names[0]] + a].to_numpy() - os_df[marker_body_dict[marker_names[1]] + a].to_numpy())
    if(len(dist) == 0):
        dist = dist_temp
    else:
        dist = dist+dist_temp
        
        
    








