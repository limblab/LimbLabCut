# -*- coding: utf-8 -*-
"""
Created on Tue Apr  5 16:08:50 2022

@author: Joseph Sombeck
"""

#!python3
# -*- coding: utf-8 -*-
"""
NCams Toolbox
Copyright 2019-2020 Charles M Greenspon, Anton Sobinov
https://github.com/CMGreenspon/NCams

Functions related to setting up and analyzing inverse kinematics using OpenSim (SimTK).
"""
import ntpath
import csv
import math
from copy import deepcopy
import xml.etree.ElementTree as ET
import warnings

import numpy
import scipy.signal


IK_XML_STR = r'''<?xml version="1.0" encoding="UTF-8" ?>
<OpenSimDocument Version="40000">
    <InverseKinematicsTool>
        <!--Directory used for writing results.-->
        <results_directory>./</results_directory>
        <!--Directory for input files-->
        <input_directory />
        <!--Name of the model file (.osim) to use for inverse kinematics.-->
        <model_file>Unassigned</model_file>
        <!--A positive scalar that weights the relative importance of satisfying constraints. A weighting of 'Infinity' (the default) results in the constraints being strictly enforced. Otherwise, the weighted-squared constraint errors are appended to the cost function.-->
        <constraint_weight>Inf</constraint_weight>
        <!--The accuracy of the solution in absolute terms. Default is 1e-5. It determines the number of significant digits to which the solution can be trusted.-->
        <accuracy>1.0000000000000001e-05</accuracy>
        <!--Markers and coordinates to be considered (tasks) and their weightings. The sum of weighted-squared task errors composes the cost function.-->
        <IKTaskSet>
            <objects />
            <groups />
        </IKTaskSet>
        <!--TRC file (.trc) containing the time history of observations of marker positions obtained during a motion capture experiment. Markers in this file that have a corresponding task and model marker are included.-->
        <marker_file>Unassigned</marker_file>
        <!--The name of the storage (.sto or .mot) file containing the time history of coordinate observations. Coordinate values from this file are included if there is a corresponding model coordinate and task. -->
        <coordinate_file>Unassigned</coordinate_file>
        <!--The desired time range over which inverse kinematics is solved. The closest start and final times from the provided observations are used to specify the actual time range to be processed.-->
        <time_range> 0 1</time_range>
        <!--Flag (true or false) indicating whether or not to report marker errors from the inverse kinematics solution.-->
        <report_errors>true</report_errors>
        <!--Name of the resulting inverse kinematics motion (.mot) file.-->
        <output_motion_file>out_inv_kin.mot</output_motion_file>
        <!--Flag indicating whether or not to report model marker locations. Note, model marker locations are expressed in Ground.-->
        <report_marker_locations>false</report_marker_locations>
    </InverseKinematicsTool>
</OpenSimDocument>
'''


def triangulated_to_trc(triang_csv, trc_file, marker_name_dict, data_unit_convert=None,
                        rate=50, repeat=0, zero_marker='scapula_anterior', frame_range=None,
                        runtime_data_check=None, rotation=None,
                        ik_file=None, ik_weight_type='nans',
                        ik_xml_str=None, ik_out_mot_file='out_inv_kin_mot',
                        static_triang_csv=None):
    '''Transforms triangulated data from NCams/DLC format into OpenSim trc.

    Arguments:
        triang_csv {string} -- get the triangulated data from this file.
        trc_file {string} -- output filename.
        marker_name_dict {dict} -- dictionary relating names of markers in triangulated file to the
            names in the output trc file.

    Keyword Arguments:
        data_unit_convert {lambda x} -- transform values in units. OSim usually expects meters.
            By default, transforms decimeters into m. (default: {lambda x: x*100})
        rate {number} -- framerate of the data. (default: {50})
        repeat {number} -- add copies of the datapoints to the end of the output file. Useful when
            OSim has a problem visualising too few points. (default: {0})
        zero_marker {str or None} -- shift all data so that the marker with this name is (0,0,0) at
            frame 0. If None, no shift of the data is happening (default: {'scapula_anterior'})
        frame_range {2-list of numbers or None} -- frame range to export from the file. If a tuple
            then indicates the start and end frame number, including both as an interval. If None
            then all frames will be used. If frame_range[1] is None, continue until the last frame.
            (default: None)
        runtime_data_check {function} -- print custom information about the data while it is being
            transferred. The function should accept the following positional arguments:
            (frame_number, value_dict)
                frame_number {int} -- frame number id of the datum being processed.
                value_dict {dict} -- dictionary relating the maker name in NCams/DLC style to the
                    marker locations (x, y, z) in units after the data_unit_convert.
            (default: {pass})
        rotation {function} -- is applied to every point (x,y,z). Is supposed to accept a list with
            3 numbers (vector in NCams coordinate system) and return a list with three numbers
            (vector in OSim coordinate system). (default: {returns same vector})
        ik_file {str or None} -- makes a config file to run inverse kinematics in OSim. If None, the
            it is not created. (default: None)
        ik_weight_type {'nans', 'ones', 'likelihood'} -- an algorithm to pick a weight for each
            marker:
            'nans' -- weight for a marker equals to 1 - portion of points where it was NaN.
            'ones' -- all weights are 1.
            'likelihood' -- not implemented.
            (default: 'nans')
        ik_xml_str {str} -- XML structure of the output inverse kinematic file. See
            ncams.inverse_kinematics.IK_XML_STR for an example of input. (default:
            ncams.inverse_kinematics.IK_XML_STR)
        ik_out_mot_file {str} --  filename of the output inverse kinematics file.
            {default: 'out_inv_kin_mot'}
        static_triang_csv {str} -- additional triangulated data file, specifically for static
            markers that don't move during experiment. {default: None}
    '''
    if data_unit_convert is None:
        data_unit_convert = lambda x: x*100  # dm to mm
    period = 1./rate
    if rotation is None:
        rotation = lambda x: x

    if frame_range is None:
        with open(triang_csv, 'r') as f:
            n_frames = len(f.readlines()) - 2
    elif frame_range[1] is None:
        with open(triang_csv, 'r') as f:
            n_frames = len(f.readlines()) - 2 - frame_range[0]
    else:
        n_frames = frame_range[1] - frame_range[0] + 1

    s_n_bodyparts = 0
    s_bodyparts = []
    s_vals = []
    if static_triang_csv is not None:
        with open(static_triang_csv, 'r') as sfin:
            rdr = csv.reader(sfin)

            li = next(rdr)
            li2 = next(rdr)  # flavor text
            li2 = next(rdr)
            s_n_bodyparts = int((len(li)-1)/3)
            s_vals = []
            for i in range(s_n_bodyparts):
                if li[1+i*3] in marker_name_dict.keys():
                    s_bodyparts.append(marker_name_dict[li[1+i*3]])
                    s_vals.append([li2[1+i*3], li2[1+i*3+1], li2[1+i*3+2]])
            s_n_bodyparts = len(s_bodyparts)

    with open(triang_csv, 'r') as fin, open(trc_file, 'w', newline='') as fou:
        rdr = csv.reader(fin)
        wrr = csv.writer(fou, delimiter='\t', dialect='excel-tab')

        li = next(rdr)
        n_bodyparts = int((len(li)-1)/3)
        bp_xyz_indcs = []
        bodyparts = []
        for i in range(n_bodyparts):
            if li[1+i*3] in marker_name_dict.keys():
                bodyparts.append(li[1+i*3])
                bp_xyz_indcs.append([1+i*3, 1+i*3+1, 1+i*3+2])
        n_bodyparts = len(bodyparts)

        wrr.writerow(['PathFileType', '4', '(X/Y/Z)', ntpath.basename(trc_file)])
        wrr.writerow(['DataRate', 'CameraRate', 'NumFrames', 'NumMarkers', 'Units', 'OrigDataRate',
                      'OrigDataStartFrame', 'OrigNumFrames'])
        wrr.writerow([rate, rate, n_frames*(repeat+1), n_bodyparts+s_n_bodyparts, 'mm', rate, 1, 1])
        lo = ['Frame#', 'Time']
        for bp in bodyparts:
            lo += [marker_name_dict[bp], '', '']
        for bp in s_bodyparts:
            lo += [bp, '', '']
        wrr.writerow(lo)

        lo = ['', '']
        for ibp in range(n_bodyparts+s_n_bodyparts):
            lo += ['X{}'.format(ibp+1), 'Y{}'.format(ibp+1), 'Z{}'.format(ibp+1)]
        wrr.writerow(lo)
        wrr.writerow([])

        zero_index = None
        if repeat > 0:
            data_copy = []

        next(rdr)
        # skip the first frame until the desired frame_range
        if frame_range is not None and frame_range[0] > 0:
            while int(next(rdr)[0]) < frame_range[0] - 1:
                pass

        num_dats = dict(zip(bodyparts, [0]*n_bodyparts))

        broke = False
        for i, li in enumerate(rdr):
            # when to stop based on frame_range
            if (frame_range is not None and frame_range[1] is not None and
                    int(li[0]) > frame_range[1]):
                broke = True
                break

            # first iteration, set up zeros
            if zero_index is None:
                if zero_marker is None:
                    zero_index = -1
                    zero_x = 0
                    zero_y = 0
                    zero_z = 0
                else:
                    zero_index = bodyparts.index(zero_marker)
                    zero_x = float(li[bp_xyz_indcs[zero_index][0]])
                    zero_y = float(li[bp_xyz_indcs[zero_index][1]])
                    zero_z = float(li[bp_xyz_indcs[zero_index][2]])

            # set up the dictionary for all values
            value_dict = {}
            for bp, (ix, iy, iz) in zip(bodyparts, bp_xyz_indcs):
                if 'nan' in (li[ix].lower(), li[iy].lower(), li[iz].lower()):
                    value_dict[bp] = ['', '', '']
                else:
                    value_dict[bp] = rotation([[data_unit_convert(float(li[ix])-zero_x),
                                                data_unit_convert(float(li[iy])-zero_y),
                                                data_unit_convert(float(li[iz])-zero_z)]])
                    num_dats[bp] += 1

            lo = [i+1, i*period]
            for bp in bodyparts:
                lo += value_dict[bp]

            for v in s_vals:
                lo += rotation([[data_unit_convert(float(v[0])-zero_x),
                                 data_unit_convert(float(v[1])-zero_y),
                                 data_unit_convert(float(v[2])-zero_z)]])

            if repeat > 0:
                data_copy.append(deepcopy(lo[2:]))

            # OpenSim4.0 cannot read the line properly when the last value is
            # empty and wants an additional tab:
            if lo[-1] == '':
                lo.append('')

            wrr.writerow(lo)

            # print a runtime report
            if runtime_data_check is not None:
                runtime_data_check(i, value_dict)
        if broke:
            time_range = [0, (i-1)*period]
        else:
            time_range = [0, i*period]

        print('Portion of the data being data and not NaNs:')
        print('\n'.join('\t{}: {:.3f}'.format(marker_name_dict[bp], num_dats[bp]/n_frames)
                        for bp in bodyparts))

        # add copies
        frame_start_copy = i+2
        for i in range(repeat):
            for j, dc in enumerate(data_copy):
                frame_n = frame_start_copy+i*len(data_copy)+j
                lo = [frame_n, (frame_n-1)*period]
                lo += dc
                wrr.writerow(lo)
        if repeat > 0:
            print('Added {} copies of data.'.format(repeat))

    # make inverse kinematic config file for OSim
    if ik_file is not None:
        if ik_xml_str is None:
            ik_xml_str = IK_XML_STR
        print('Making IK file {}'.format(ik_file))
        root = ET.fromstring(ik_xml_str)
        if root.tag != 'OpenSimDocument':
            raise ValueError('Wrong structure of the IK string. OpenSimDocument is not present at '
                             'top-level.')

        ikt = root.find('InverseKinematicsTool')
        if ikt is None:
            # default structure of the IKT, like in the IK_XML_STR
            ikt = ET.Element('InverseKinematicsTool')
            ikt.append(ET.Element('results_directory', text='./'))
            ikt.append(ET.Element('input_directory'))
            ikt.append(ET.Element('model_file', text='Unassigned'))
            ikt.append(ET.Element('constraint_weight', text='Inf'))
            ikt.append(ET.Element('accuracy', text='1.e-05'))
            ikt.append(ET.Element('coordinate_file', text='Unassigned'))
            ikt.append(ET.Element('report_errors', text='true'))
            ikt.append(ET.Element('report_marker_locations', text='false'))
            root.append(ikt)

        ikts = ikt.find('IKTaskSet')
        if ikts is None:
            ikts = ET.Element('IKTaskSet')
            ikts.append(ET.Element('groups'))

        iktso = ikts.find('objects')
        if iktso is None:
            iktso = ET.Element('objects')
            ikts.append(iktso)

        if iktso.text is None or len(iktso.text) == 0:
            iktso.text = '\n' + ' '*16

        if iktso.tail is None or len(iktso.tail) == 0:
            pass
        iktso.tail = '\n' + ' '*12

        for bp in bodyparts:
            bpe = ET.Element('IKMarkerTask')
            bpe.set('name', marker_name_dict[bp])
            bpe.text = '\n' + ' '*20
            bpe.tail = '\n' + ' '*16

            # calculate the weight of the marker
            if ik_weight_type == 'nans':
                bp_weight = num_dats[bp]/n_frames
            elif ik_weight_type == 'ones':
                bp_weight = 1
            elif ik_weight_type == 'likelihood':
                raise NotImplementedError('Using likelihood for estimation of the marker weight.')

            if bp_weight < 1e-8:
                bp_apply = 'false'
            else:
                bp_apply = 'true'

            bpe_a = ET.Element('apply')
            bpe_a.text = bp_apply
            bpe_a.tail = '\n' + ' '*20
            bpe.append(bpe_a)
            bpe_w = ET.Element('weight')
            bpe_w.text = str(bp_weight)
            bpe_w.tail = '\n' + ' '*16
            bpe.append(bpe_w)

            iktso.append(bpe)

        for s_bp in s_bodyparts:
            bpe = ET.Element('IKMarkerTask')
            bpe.set('name', s_bp)
            bpe.text = '\n' + ' '*20
            bpe.tail = '\n' + ' '*16

            # calculate the weight of the marker
            bp_weight = 1
            bp_apply = 'true'

            bpe_a = ET.Element('apply')
            bpe_a.text = bp_apply
            bpe_a.tail = '\n' + ' '*20
            bpe.append(bpe_a)
            bpe_w = ET.Element('weight')
            bpe_w.text = str(bp_weight)
            bpe_w.tail = '\n' + ' '*16
            bpe.append(bpe_w)

            iktso.append(bpe)


        ikt_tr = ikt.find('time_range')
        if ikt_tr is None:
            ikt_tr = ET.Element('time_range')
            ikt.append(ikt_tr)
        ikt_tr.text = '{} {}'.format(time_range[0], time_range[1])

        ikt_mf = ikt.find('marker_file')
        if ikt_mf is None:
            ikt_mf = ET.Element('marker_file')
            ikt.append(ikt_mf)
        ikt_mf.text = trc_file

        ikt_omf = ikt.find('output_motion_file')
        if ikt_omf is None:
            ikt_omf = ET.Element('output_motion_file')
            ikt.append(ikt_omf)
        ikt_omf.text = ik_out_mot_file

        tree = ET.ElementTree(element=root)
        tree.write(ik_file, encoding='UTF-8', xml_declaration=True)


def remove_empty_markers_from_trc(trc_filename):
    '''Removes markers from a trc file that do not have any data points.

    Arguments:
        trc_filename {str} -- filename to process.
    '''
    bodyparts, frame_numbers, times, points, rate, units = import_trc(trc_filename)

    for ibp in reversed(range(len(bodyparts))):
        if all([numpy.isnan(points[iframe][ibp][0]) for iframe in range(len(points))]):
            print('Removing bodypart {} from trc file {}.'.format(bodyparts[ibp], trc_filename))
            del bodyparts[ibp]
            for iframe in range(len(points)):
                del points[iframe][ibp]

    print('{} bodyparts left: {}.'.format(len(bodyparts), ', '.join(bodyparts)))

    export_trc(trc_filename, bodyparts, frame_numbers, times, points, rate, units)


def rdc_touchpad3d(frame_number, value_dict, dist_desired=(105, 79, 105, 79), warn_threshold=5,
                   marker_name_dict=None):
    '''Runtime data check example, checks if TouchPad3D markers are present and measures deviation
    from the physical measurements of the TouchPad3D.

    Arguments:
        frame_number {int} -- frame number id of the datum being processed.
        value_dict {dict} -- dictionary relating the maker name in NCams/DLC style to the marker
            locations (x, y, z) in units after the data_unit_convert.

    Keyword Arguments:
        dist_desired {tuple} -- measurements of each side (left-front, front-right, roght-back,
            back-left) of the touchpad. (default: {(105, 79, 105, 79) mm})
        warn_threshold {number} -- threshold in mm for warning a user if the touchpad dimensions
            seem wrong. (default: {5} mm)
        marker_name_dict {dict} -- dictionary relating DLC/NCams names of markers to the OpenSim
            names. (default: {None})
    '''
    lf_desired, fr_desired, rb_desired, bl_desired = dist_desired
    def dist_f(fs, ss):
        if fs not in value_dict.keys() or ss not in value_dict.keys():
            return math.nan
        if len(value_dict[fs][0]) == 0 or len(value_dict[ss][0]) == 0:
            return math.nan
        return ((value_dict[fs][1] - value_dict[ss][1])**2 +
                (value_dict[fs][2] - value_dict[ss][2])**2 +
                (value_dict[fs][3] - value_dict[ss][3])**2) ** 0.5

    if marker_name_dict is None:
        marker_name_dict = dict(zip(('tp_left_c', 'tp_front_c', 'tp_right_c', 'tp_back_c'),
                                    ('tp_left_c', 'tp_front_c', 'tp_right_c', 'tp_back_c')))

    lf = dist_f('tp_left_c', 'tp_front_c')
    fr = dist_f('tp_front_c', 'tp_right_c')
    rb = dist_f('tp_right_c', 'tp_back_c')
    bl = dist_f('tp_back_c', 'tp_left_c')
    warning_s = ''
    if abs(lf-lf_desired) > warn_threshold and abs(fr-fr_desired) > warn_threshold:
        warning_s += ' Recommend dropping {} marker from IK.'.format(
            marker_name_dict['tp_front_c'])
    if abs(fr-fr_desired) > warn_threshold and abs(rb-rb_desired) > warn_threshold:
        warning_s += ' Recommend dropping {} marker from IK.'.format(
            marker_name_dict['tp_right_c'])
    if abs(rb-rb_desired) > warn_threshold and abs(bl-bl_desired) > warn_threshold:
        warning_s += ' Recommend dropping {} marker from IK.'.format(
            marker_name_dict['tp_back_c'])
    if abs(bl-bl_desired) > warn_threshold and abs(lf-lf_desired) > warn_threshold:
        warning_s += ' Recommend dropping {} marker from IK.'.format(
            marker_name_dict['tp_left_c'])
    print('Frame {} distances: lf: {} mm, fr: {} mm, rb: {} mm, bl: {} mm.{}'.format(
        frame_number, lf, fr, rb, bl, warning_s))


def import_mot(fname):
    '''Import OpenSim motion file into a python structure.

    Arguments:
        fname {str} -- motion file.

    Returns a list:
        dof_names {list of str} -- names of DOFs.
        times {list of numbers} -- time series.
        dofs {list} -- each item corresponds to values for that DOF for each frame.
            dofs[iDOF][iTime]
    '''
    with open(fname, 'r') as f:
        rdr = csv.reader(f, dialect='excel-tab')

        l = next(rdr)
        while len(l) < 1 or not l[0].strip().lower() == 'time':
            l = next(rdr)

        dof_names = [i.strip() for i in l[1:]]

        times = []
        dofs = [[] for _ in dof_names]

        for li in rdr:
            times.append(float(li[0]))
            for idof, vdof in enumerate(li[1:]):
                dofs[idof].append(float(vdof))
    return dof_names, times, dofs


def export_mot(fname, dof_names, times, dofs):
    '''Exports python structures into a motion file for OpenSim.

    Arguments:
        fname {str} -- filename of the mot file to output into.
        dof_names {list of str} -- each element is the DOF string name.
        times {list of numbers} -- time series.
        dofs {list} -- each item corresponds to values for that DOF for each frame.
    '''
    with open(fname, 'w', newline='') as f:
        wrr = csv.writer(f, dialect='excel-tab')

        wrr.writerow(['Coordinates'])
        wrr.writerow(['version=1'])
        wrr.writerow(['nRows={}'.format(len(times))])
        wrr.writerow(['nColumns={}'.format(len(dof_names)+1)])
        wrr.writerow(['inDegrees=yes'])
        wrr.writerow([])
        wrr.writerow(['Units are S.I. units (second, meters, Newtons, ...)'])
        wrr.writerow(['Angles are in degrees.'])
        wrr.writerow([])
        wrr.writerow(['endheader'])
        wrr.writerow(['time'] + dof_names)

        for itime, time in enumerate(times):
            wrr.writerow([time] + [dof_vals[itime] for dof_vals in dofs])


def import_trc(filename):
    '''Import OpenSim trc file into a Python structure format.

    Arguments:
        filename {str} -- trc file name.
    Output:
        bodyparts {list of str} -- names of markers.
        frame_numbers {list of ints} -- Frame # column.
        times {list of floats} -- Time column
        points {array NFrames X NBodyparts X 3} -- [iframe][ibodypart][0:x,1:y,2:z]
        rate {float} -- DataRate.
        units {str} - units of the data.
    '''
    with open(filename, 'r') as fin:
        rdr = csv.reader(fin, delimiter='\t', dialect='excel-tab')

        li = next(rdr)  # flavor text
        li = next(rdr)  # flavor text

        li = next(rdr)
        if not li[0] == li[1] or not li[0] == li[5]:
            warnings.warn('DataRate, CameraRate or OrigDataRate do not match. Using DataRate.')
        rate = float(li[0])
        units = li[4]

        li = next(rdr)
        bodyparts = li[slice(2, len(li), 3)]

        li = next(rdr)
        li = next(rdr)

        frame_numbers = []
        times = []
        points = []
        for li in rdr:
            if len(li) == 0:
                continue
            frame_numbers.append(int(li[0]))
            times.append(float(li[1]))
            points.append([])
            for ibp in range(len(bodyparts)):
                points[-1].append([])
                if li[2+ibp*3] == '':
                    points[-1][-1].append(numpy.nan)
                    points[-1][-1].append(numpy.nan)
                    points[-1][-1].append(numpy.nan)
                else:
                    points[-1][-1].append(float(li[2+ibp*3]))
                    points[-1][-1].append(float(li[2+ibp*3+1]))
                    points[-1][-1].append(float(li[2+ibp*3+2]))
    return bodyparts, frame_numbers, times, points, rate, units


def export_trc(filename, bodyparts, frame_numbers, times, points, rate, units='mm'):
    '''Exports marker data into OpenSim-compatible trc file.

    Arguments:
        filename {str} -- output file name.
        bodyparts {list of str} -- names of markers.
        frame_numbers {list of ints} -- Frame # column.
        times {list of floats} -- Time column
        points {array NFrames X NBodyparts X 3} -- [iframe][ibodypart][0:x,1:y,2:z]
        rate {float} -- DataRate.
    Keyword Arguments:
        units {str} - units of the data. {default: 'mm'}
    '''
    n_bodyparts = len(bodyparts)
    n_frames = len(frame_numbers)

    with open(filename, 'w', newline='') as fou:
        wrr = csv.writer(fou, delimiter='\t', dialect='excel-tab')

        wrr.writerow(['PathFileType', '4', '(X/Y/Z)', ntpath.basename(filename)])
        wrr.writerow(['DataRate', 'CameraRate', 'NumFrames', 'NumMarkers', 'Units', 'OrigDataRate',
                      'OrigDataStartFrame', 'OrigNumFrames'])
        wrr.writerow([rate, rate, n_frames, n_bodyparts, units, rate, 1, 1])
        lo = ['Frame#', 'Time']
        for bp in bodyparts:
            lo += [bp, '', '']
        wrr.writerow(lo)

        lo = ['', '']
        for ibp in range(n_bodyparts):
            lo += ['X{}'.format(ibp+1), 'Y{}'.format(ibp+1), 'Z{}'.format(ibp+1)]
        wrr.writerow(lo)
        wrr.writerow([])

        for frame_number, time, point in zip(frame_numbers, times, points):
        # for i, li in enumerate(rdr):
            lo = [frame_number, time]
            for ibp in range(n_bodyparts):
                if numpy.isnan(point[ibp][0]):
                    lo += ['', '', '']
                else:
                    lo += point[ibp]

            # OpenSim4.0 cannot read the line properly when the last value is
            # empty and wants an additional tab:
            if lo[-1] == '':
                lo.append('')

            wrr.writerow(lo)


def smooth_motion(in_fname, ou_fname, median_kernel_size=11, ou_rate=None, filter_1d=None):
    '''Filters the motion from a file and saves it.

    Arguments:
        in_fname {str} -- filename with inverse kinematics motion to filter.
        ou_fname {str} -- filename for output of the filtered kinematics.

    Keyword Arguments:
        median_kernel_size {odd int} -- size of the kernel for median filter. Has to be odd.
            (default: 11)
        ou_rate {number} -- output rate. If not equal to in_rate, the signal is going to be
            resampled before median filter. (default: {same as input rate measured from input motion
            file})
        filter_1d {callable} -- custom filter to run on each DOF. Should be an executeable that
            accepts two arguments: time series, dof values. (default: {None})
    '''
    # load
    dof_names, times, dofs = import_mot(in_fname)

    in_rate = numpy.mean(numpy.diff(times))
    if ou_rate is None:
        ou_rate = in_rate

    # resample
    if in_rate != ou_rate:
        num_ou = int(len(times)*ou_rate/in_rate)
        for idof in range(len(dofs)):
            dofs[idof] = scipy.signal.resample(dofs[idof], num_ou, t=times, window=None)[0]
        times = scipy.signal.resample(dofs[0], num_ou, t=times, window=None)[1]
        times = [t/ou_rate*in_rate for t in times]

    # median filter
    for idof in range(len(dofs)):
        dofs[idof] = scipy.signal.medfilt(dofs[idof], kernel_size=median_kernel_size)

    # custom filter
    if filter_1d is not None:
        for idof in range(len(dofs)):
            dofs[idof] = filter_1d(times, dofs[idof])

    # output
    export_mot(ou_fname, dof_names, times, dofs)