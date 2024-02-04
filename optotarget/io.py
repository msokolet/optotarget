'''
This module contains functions for loading and saving objects, as well as controlling the NI card.
'''
import os
import datetime

import numpy as np
import nidaqmx
from scipy import signal
from nidaqmx import stream_writers

import optotarget as ot

def analog_out_single(card, channel, val, cwd):
    '''
    Set the analog output channel on the specified card to this value.
    '''
    try:
        task = nidaqmx.Task()
        task.ao_channels.add_ao_voltage_chan(f'{card}/ao{channel}')
        task.write(float(val))
        task.close()
    except:
        log_status('Could not connect to NI card. Please set name and press test.', cwd)
        

def analog_out_wave(card, channel, sr, vec):
    '''
    Output a continuous signal.
    '''
    # create the output task
    task = nidaqmx.Task()
    # add the analog output channel
    task.ao_channels.add_ao_voltage_chan(f'{card}/ao{channel}')
    # set the sample rate
    task.timing.cfg_samp_clk_timing(sr, samps_per_chan=vec.shape[0], sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS)
    # write the output vector continuous, restarting automatically upon the end
    writer = stream_writers.AnalogSingleChannelWriter(task.out_stream, auto_start=True)
    writer.write_many_sample(vec, timeout=nidaqmx.constants.WAIT_INFINITELY)

    return task

def analog_out_pulse(card, channel, sr, vec):
    '''
    Output a pulse.
    '''
    # create the output task
    task = nidaqmx.Task()
    # add the analog output channel
    task.ao_channels.add_ao_voltage_chan(f'{card}/ao{channel}')
    # set the sample rate
    task.timing.cfg_samp_clk_timing(sr, samps_per_chan=vec.shape[0], sample_mode=nidaqmx.constants.AcquisitionType.FINITE)
    # write an output pulse
    task.write(vec, auto_start=True)
    task.wait_until_done(timeout=nidaqmx.constants.WAIT_INFINITELY)
    task.close()

def start_protocol(channels, sr, trigger, output, stim_prob, cwd):
    '''
    Start the protocol, which will loop through the output matrix and apply the stimulation.
    '''
    # create the out_matrix to be used in the current protocol
    regions, intensity_matrix, x_matrix, y_matrix = output['regions'], output['intensity_matrix'], \
                                                        output['x_matrix'], output['y_matrix']
    while True: # protocol loop
        # first, decide whether to do control stimulation or not, based on stim_prob
        if 100*np.random.random() > stim_prob:
            # if not, set the row to zero
            group = 0
        else:
            # randomally select the current row of the output from all options above 0
            if intensity_matrix.shape[0] == 1:
                group = 0
            else:
                group = np.random.randint(1, intensity_matrix.shape[0])
        # send the region name to connection
        if group == 0:
            log_status('Waiting to apply control stimulation.', cwd)
        else:
            log_status(f'Waiting to apply {regions[group]} stimulation.', cwd)
        # combine the intensity_matrix row with a vector of x and y values, extending the x and y values to the same dimension
        out_matrix = np.vstack((intensity_matrix[group, :], x_matrix[group, :], y_matrix[group, :]))
        # create the output task
        task = nidaqmx.Task()
        # add the analog output channels
        task.ao_channels.add_ao_voltage_chan(channels)
        # set the sample rate
        task.timing.cfg_samp_clk_timing(sr, samps_per_chan=out_matrix.shape[1])
        # configure trigger
        task.triggers.start_trigger.cfg_dig_edge_start_trig(trigger)
        # write the output matrix
        writer = stream_writers.AnalogMultiChannelWriter(task.out_stream, auto_start=False)
        writer.write_many_sample(out_matrix)
        # start the task
        task.start()
        task.wait_until_done(timeout=nidaqmx.constants.WAIT_INFINITELY)
        time = datetime.datetime.now()
        # log the completed stimulation to file along with a timestamp
        log_last_stimulation(regions[group], cwd)
        # print that the stimulation was given
        print(f'{time}: {regions[group]} stimulation given.')
        # log it to file
        log_stimulation(regions[group], time, cwd)
        task.stop()
        task.close()

def reset(ni_card, cwd):
    '''
    Reset the NI card.
    '''
    try:
        device = nidaqmx.system.System.local().devices[ni_card]
        device.reset_device()
        log_status('Ready.', cwd)
    except: # if could not reset - display status
        log_status('Could not connect to NI card. Please set name and press test.', cwd)

def log_last_stimulation(region, cwd):
    '''
    Log the last stimulation to file.
    '''
    # log the completed stimulation to file, overwriting the previous file
    log_file = os.path.join(cwd, 'stim.txt')
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f'{region}')

def log_status(status, cwd):
    '''
    Log the current status to file.
    '''
    # log the completed stimulation to file along with a timestamp, overwriting the previous file
    log_file = os.path.join(cwd, 'status.txt')
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(status)

def log_stimulation(region, time, cwd):
    '''
    Log the completed stimulation to file.
    '''
    # log the completed stimulation to file along with a timestamp, overwriting the previous file
    log_file = os.path.join(cwd, 'log.txt')
    # append or create
    with open(log_file, 'a+', encoding='utf-8') as f:
        f.write(f'{region} at {time}')
        f.write('\n')

def create_stim(times, freq, sin, duty_cycle):
    '''
    Create a stimulation vector.
    '''
    if sin:
        stim = (np.sin(2 * np.pi * times * freq) + 1)/2
    else:
        stim = (signal.square(2 * np.pi * times * freq, duty=duty_cycle/100) + 1)/2

    return stim
