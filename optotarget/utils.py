'''
This module contains various functions for calculating and manipulating data.
'''
import numpy as np
from PyQt6 import QtWidgets

import optotarget as ot

def create_output(ui):
    '''
    Create the output matrix based on the values in the targets table.
    '''
    # create a matrix of values to output
    output = {}
    on_points = int(ui.on_dur.value()*ui.sample_rate.value())
    taper_points = int(ui.taper_dur.value()*ui.sample_rate.value())
    total_time = ui.on_dur.value() + ui.taper_dur.value()
    times = np.linspace(0, total_time, on_points + taper_points)
    # first, extract the groups - 4th column of the targets table
    groups = np.zeros(ui.targets_table.rowCount())
    for row in range(ui.targets_table.rowCount()):
        groups[row] = int(ui.targets_table.item(row, 3).text())
    n_groups = int(np.max(groups))+1
    # second, create an array sized by the number of unique groups, with 1 for indices where more than 1 the value are present, and 0 otherwise
    multiple = np.zeros(n_groups+1)
    for pair in range(n_groups):
        multiple[pair] = np.sum(groups == pair) >= 2
    # then, create a matrix of zeros for intensity, and corresponding x and y matrixtors
    intensity_matrix = np.zeros((n_groups, times.shape[0]))
    x_matrix = np.zeros((n_groups, times.shape[0]))
    y_matrix = np.zeros((n_groups, times.shape[0]))
    # create an empty vector for the region names
    regions = np.empty(n_groups, dtype=object)
    # then, fill in the values, depending on bilaterality
    for group in range(n_groups):
        rows = np.where(groups == group)[0]
        # fill the regions_vec at the current group with the region names from the rows, separated by a comma
        regions[group] = ', '.join([ui.targets_table.verticalHeaderItem(row).text() for row in rows])
        if multiple[group]:
            intensity_vec = ot.create_stim(times, ui.stim_freq.value(), ui.sin_stim.isChecked(), ui.duty_cycle.value())
            intensity_vec[-taper_points:] = intensity_vec[-taper_points:]*np.linspace(1, 0, taper_points)
            # get the intensity values from the table
            intensity_vals = np.array([float(ui.targets_table.item(row, 0).text()) for row in rows])
            # set the overall intensity as the mean intensity times the number of regions
            intensity =  np.mean(intensity_vals)
            # # also multiply by a compensation due to the switch_dur compared to 1000/switch_freq
            # full_dur = 1000/ui.switch_freq.value()
            # on_dur = full_dur - ui.switch_dur.value()
            # intensity = intensity*full_dur/on_dur
            intensity_matrix[group, :] = intensity_vec*intensity
            # alternate between the locations while keeping constant intensity
            x_positions = np.array([float(ui.targets_table.item(row, 1).text()) for row in rows])
            # fit every x positions per switch_freq
            cycle_points = int(np.floor(ui.sample_rate.value()/ui.switch_freq.value()))
            x_positions_cycle = np.repeat(x_positions, cycle_points)
            x_matrix[group, :] = np.tile(x_positions_cycle, int(np.ceil(times.shape[0]/cycle_points)))[:times.shape[0]]
            y_positions = np.array([float(ui.targets_table.item(row, 2).text()) for row in rows])
            y_positions_cycle = np.repeat(y_positions, cycle_points)
            y_matrix[group, :] = np.tile(y_positions_cycle, int(np.ceil(times.shape[0]/cycle_points)))[:times.shape[0]]
            # finally, zero the intensity at transitions for the duration set by switch_dur
            switch_points = int(np.floor(ui.switch_dur.value()*ui.sample_rate.value()/1000))
            # find the indices of changes in x or y
            changes = np.where((np.diff(x_matrix[group, :]) != 0)|(np.diff(y_matrix[group, :]) != 0))[0]
            # set the intensity to zero one point before these indices
            for change in changes:
                intensity_matrix[group, (change-1):(change+switch_points-1)] = 0
        else:
            row = rows[0]
            intensity_vec =  ot.create_stim(times, ui.stim_freq.value(), ui.sin_stim.isChecked(), ui.duty_cycle.value())
            intensity_vec[-taper_points:] = intensity_vec[-taper_points:]*np.linspace(1, 0, taper_points)
            # get the intensity value from the table
            intensity = float(ui.targets_table.item(row, 0).text())
            # for every row of the matrix, first set the on_dur portion equal to a sinusoid with frequency equal to freq and amplitude equal to intensity
            intensity_matrix[group, :] = intensity_vec*intensity
            # set the x and y values to the corresponding values in the table
            x_matrix[group, :] = np.tile(float(ui.targets_table.item(row, 1).text()), intensity_matrix.shape[1])
            y_matrix[group, :] = np.tile(float(ui.targets_table.item(row, 2).text()), intensity_matrix.shape[1])

    # return the matrix and matrixtors
    output = {'regions': regions, 'intensity_matrix': intensity_matrix, 'x_matrix': x_matrix, 'y_matrix': y_matrix}

    return output


def get_groups(targets_table, cur_row=None, new_group=None):
    '''
    Get the groups from the targets table.
    '''
    groups = np.zeros(targets_table.rowCount())
    for row in range(targets_table.rowCount()):
        groups[row] = int(targets_table.item(row, 3).text())
    if cur_row is not None:
        groups[cur_row] = new_group

    return groups


def message(text):
    '''
    Show a message box with the specified text.
    '''
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Icon.Information)
    msg.setText(text)
    msg.exec()
    