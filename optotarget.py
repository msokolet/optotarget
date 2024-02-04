'''
This code is for the optotarget GUI. It allows you to create targets with a name,
intensity, x_val, y_val, and group. You can create a new target, save a 
selected target, or delete a selected target. The targets are stored in a table 
and can be exported to a csv file.
Author: Michael Sokoletsky, Ilan Lampl lab, Weizmann Institute of Science, 2024
'''

import sys
import os
import multiprocessing
import warnings

import pyqtgraph as pg
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QFileDialog
from PyQt6 import uic, QtGui, QtCore

import optotarget as ot

# options
pg.setConfigOption('background', 'w')
warnings.filterwarnings('ignore')

class OptoTarget(QMainWindow):
    '''
    The GUI class for the optotarget GUI. It allows you to create targets with 
    a name, intensity, x_val, y_val, and group. You can create a new target, 
    save a selected target, or delete a selected target. The targets are stored 
    in a table and can be exported to a csv file.
    '''
    def __init__(self):
        super().__init__()
        # set current directory to the directory of this script file
        self.cwd = os.path.dirname(os.path.realpath(__file__))

        # load the ui using loadUi with the current dir set the the dir of this file
        # note this autmatically sets the attributes of self to the ui elements
        uic.loadUi(os.path.join(self.cwd, 'optotarget.ui'), self)
        icon = QtGui.QIcon()
        # set window title
        self.setWindowTitle('OptoTarget')

        # add a menu bar and set its title to test
        self.menu_bar = self.menuBar()
        self.status = self.menu_bar.addMenu('status')

        # periodically update status every 100 ms
        self.status_timer = pg.QtCore.QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(100)

        # reset the NI card
        ot.reset(self.NI_card.text(), self.cwd)

        # set the icon to the icon file in the same folder as the program
        icon.addFile(os.path.join(self.cwd, 'icons', 'optotarget.jpg'))
        self.setWindowIcon(icon)

        # change the intensity, x_val, and y_val when the sliders are moved, and vice versa
        self.cur_intensity_slider.valueChanged.connect(self.cur_intensity_slider_changed)
        self.protocol_intensity_slider.valueChanged.connect(self.protocol_intensity_slider_changed)
        self.x_slider.valueChanged.connect(self.x_slider_changed)
        self.y_slider.valueChanged.connect(self.y_slider_changed)
        self.cur_intensity.valueChanged.connect(self.cur_intensity_changed)
        self.protocol_intensity.valueChanged.connect(self.protocol_intensity_changed)
        self.x_val.valueChanged.connect(self.x_val_changed)
        self.y_val.valueChanged.connect(self.y_val_changed)
        self.target_name.textChanged.connect(self.target_name_changed)
        self.target_group.valueChanged.connect(self.target_group_changed)

        # connect buttons to their functions
        self.create_new_btn.clicked.connect(self.create_new)
        self.del_sel_btn.clicked.connect(self.deleted_sel)
        self.del_all_btn.clicked.connect(self.delete_all)
        self.zero_all_btn.clicked.connect(self.zero_all)
        self.targets_table.itemSelectionChanged.connect(self.update_opts)
        self.save_all_btn.clicked.connect(self.save_all)
        self.load_all_btn.clicked.connect(self.load_all)
        self.switch_protocol_btn.clicked.connect(self.switch_protocol)
        self.pulse_btn.clicked.connect(self.output_pulse)
        self.test_card_btn.clicked.connect(lambda: ot.reset(self.NI_card.text(), self.cwd))

        # update the stimultation and/or stimulation plot when changing parameters
        self.on_dur.valueChanged.connect(self.update_plot)
        self.taper_dur.valueChanged.connect(self.update_plot)
        self.duty_cycle.valueChanged.connect(self.update_wave)
        self.sin_stim.toggled.connect(self.update_wave)
        self.stim_freq.valueChanged.connect(self.update_wave)
        self.sample_rate.valueChanged.connect(self.update_wave)
        self.constant_intensity_online.toggled.connect(self.cur_intensity_changed)

        # if sin_stim radio is turned on, disable duty cycle and vice versa
        self.sin_stim.toggled.connect(self.duty_cycle.setDisabled)

        self.cur_intensity.setValue(0) # zero the current intensity, just in case
        # update
        self.cur_intensity_changed()
        self.update_plot() # update the stimulation plot

        # log last stimulation as none
        ot.log_last_stimulation('none', self.cwd)

        # show the GUI, and make it pop up
        self.show()
        self.raise_()

    def update_wave(self):
        '''
        Output the new wave based on the current intensity, and update the plot
        '''
        self.output_wave()
        self.update_plot()

    def update_plot(self):
        '''
        Update the stimulation plot based on the current parameters
        '''
        on_points = int(self.on_dur.value()*self.sample_rate.value())
        taper_points = int(self.taper_dur.value()*self.sample_rate.value())
        total_time = self.on_dur.value() + self.taper_dur.value()
        times = np.linspace(0, total_time, on_points + taper_points)
        # sin
        intensity_vec = ot.create_stim(times, self.stim_freq.value(), self.sin_stim.isChecked(), self.duty_cycle.value())
        intensity_vec[-taper_points:] = intensity_vec[-taper_points:]*np.linspace(1, 0, taper_points)
        # plot using time in seconds
        times_sec = np.linspace(0, (on_points+taper_points)/self.sample_rate.value(), on_points+taper_points)
        # set plot background to white
        self.stim_plot.plot(times_sec, intensity_vec, pen=pg.mkPen('k', width=1), clear=True, autorange=True)
        # set axis labels
        self.stim_plot.setLabel('bottom', 'Time (s)')
        self.stim_plot.setLabel('left', 'Intensity')

    def cur_intensity_slider_changed(self):
        '''
        Change the current intensity based on the slider value
        '''
        self.cur_intensity.setValue(self.cur_intensity_slider.value()/1000)

    def protocol_intensity_slider_changed(self):
        '''
        Change the protocol intensity based on the slider value
        '''
        self.protocol_intensity.setValue(self.protocol_intensity_slider.value()/1000)

    def x_slider_changed(self):
        '''
        Change the x_val based on the slider value
        '''
        self.x_val.setValue(self.x_slider.value()/10000)

    def y_slider_changed(self):
        '''
        Change the y_val based on the slider value
        '''
        self.y_val.setValue(self.y_slider.value()/10000)

    def target_name_changed(self):
        '''
        Change the name of the target in the targets table based on the current row
        '''
        if self.targets_table.currentRow() != -1:
            self.targets_table.setVerticalHeaderItem(self.targets_table.currentRow(), QTableWidgetItem(self.target_name.text()))

    def cur_intensity_changed(self):
        '''
        Change the current intensity based on the current value
        '''
        self.cur_intensity_slider.setValue(int(self.cur_intensity.value()*1000))
        # if intensity is zero or is constant, simple output
        if self.cur_intensity.value() == 0 or self.constant_intensity_online.isChecked():
            self.stop_task()
            ot.analog_out_single(self.NI_card.text(), self.intensity_ch.value(), self.cur_intensity.value(), self.cwd)
        else:
            # otherwise, output a wave
            self.output_wave()

    def protocol_intensity_changed(self):
        '''
        Change the protocol intensity based on the current value
        '''
        self.protocol_intensity_slider.setValue(int(self.protocol_intensity.value()*1000))
        # save in intensity row in targets table, if one is selected
        if self.targets_table.currentRow() != -1:
            self.targets_table.setItem(self.targets_table.currentRow(), 0, QTableWidgetItem(self.protocol_intensity.text()))

    def output_wave(self):
        '''
        Output the wave based on the current intensity, and update the plot
        '''
        # if the task exists, stop it and close it
        self.stop_task()
        # output to NI card, with the channel set to intensity_ch.text() and the value set to intensity.text()
        # create one period of a sine wave with the frequency set to stim_freq.text()
        times = np.linspace(0, 1/self.stim_freq.value(), int(np.floor(self.sample_rate.value()/self.stim_freq.value())), endpoint=False)
        wave =  ot.create_stim(times, self.stim_freq.value(), self.sin_stim.isChecked(), self.duty_cycle.value())
        wave = wave*float(self.cur_intensity.text())
        # calc and print the intergral
        # integral = np.sum(wave)/self.sample_rate.value()
        # print(f'Integral: {integral}')
        self.task = ot.analog_out_wave(self.NI_card.text(), self.intensity_ch.value(), self.sample_rate.value(), wave)

    def x_val_changed(self):
        '''
        Change the x_val based on the current value
        '''
        self.x_slider.setValue(int(self.x_val.value()*10000))
        # save in x row in targets table, if one is selected
        if self.targets_table.currentRow() != -1:
            self.targets_table.setItem(self.targets_table.currentRow(), 1, QTableWidgetItem(self.x_val.text()))
        ot.analog_out_single(self.NI_card.text(), self.x_ch.value(), self.x_val.value(), self.cwd)

    def y_val_changed(self):
        '''
        Change the y_val based on the current value
        '''
        self.y_slider.setValue(int(self.y_val.value()*10000))
        # save in y row in targets table, if one is selected
        if self.targets_table.currentRow() != -1:
            self.targets_table.setItem(self.targets_table.currentRow(), 2, QTableWidgetItem(self.y_val.text()))
        ot.analog_out_single(self.NI_card.text(), self.y_ch.value(), self.y_val.value(), self.cwd)

    def target_group_changed(self):
        '''
        Change the group based on the current value
        '''
        # save in group row in targets table, if one is selected
        if self.targets_table.currentRow() != -1:
            self.targets_table.setItem(self.targets_table.currentRow(), 3, QTableWidgetItem(self.target_group.text()))

    def create_new(self):
        '''
        Create a new target in the targets table
        '''
        # a new target in target table
        self.targets_table.insertRow(self.targets_table.rowCount())
        # set row name to 'new'
        self.targets_table.setVerticalHeaderItem(self.targets_table.rowCount()-1, QTableWidgetItem('new'))
        # set intensity, x_val, y_val, and group to zero
        self.targets_table.setItem(self.targets_table.rowCount()-1, 0, QTableWidgetItem('0'))
        self.targets_table.setItem(self.targets_table.rowCount()-1, 1, QTableWidgetItem('0'))
        self.targets_table.setItem(self.targets_table.rowCount()-1, 2, QTableWidgetItem('0'))
        self.targets_table.setItem(self.targets_table.rowCount()-1, 3, QTableWidgetItem('0'))
        # select the new row
        self.targets_table.setCurrentCell(self.targets_table.rowCount()-1, 0)

    def update_opts(self):
        '''
        Update the options based on the selected target
        '''
        # if no row selected, do nothing
        if self.targets_table.currentRow() == -1:
            return
        # set options to the selected target's options
        self.target_name.setText(self.targets_table.verticalHeaderItem(self.targets_table.currentRow()).text())
        self.protocol_intensity.setValue(float(self.targets_table.item(self.targets_table.currentRow(), 0).text()))
        self.x_val.setValue(float(self.targets_table.item(self.targets_table.currentRow(), 1).text()))
        self.y_val.setValue(float(self.targets_table.item(self.targets_table.currentRow(), 2).text()))
        self.target_group.setValue(int(self.targets_table.item(self.targets_table.currentRow(), 3).text()))


    def save_all(self):
        '''
        Save all targets to a csv file in the same folder as the program, creating a new file if it doesn't exist
        '''
        # first, open a file dialog window in pyqt to get the file name - ending in .csv
        fname = QFileDialog.getSaveFileName(self, 'Save file', self.cwd, 'CSV files (*.csv)')[0]
        # if the user clicks cancel, fname will be an empty string, so return if that's the case
        if fname == '':
            return
        with open(fname, 'w', encoding='utf-8') as file:
            for row in range(self.targets_table.rowCount()):
                # start by saving the row name
                file.write(self.targets_table.verticalHeaderItem(row).text() + ',')
                # then save the intensity, x_val, y_val, and group
                for col in range(4):
                    file.write(self.targets_table.item(row, col).text() + ',')
                # end the line
                file.write('\n')


    def load_all(self):
        '''
        Load all targets from a csv file in the same folder as the program, by removing all rows and adding new ones
        '''
        # first, open a file dialog window in pyqt to get the file name - ending in .csv
        fname = QFileDialog.getOpenFileName(self, 'Open file', self.cwd, 'CSV files (*.csv)')[0]
        # if the user clicks cancel, fname will be an empty string, so return if that's the case
        if fname == '':
            return
        # if the user doesn't click cancel, open the file and read it

        with open(fname, 'r', encoding='utf-8') as file:
            self.targets_table.setRowCount(0)
            for line in file:
                row = line.split(',')
                self.targets_table.insertRow(self.targets_table.rowCount())
                self.targets_table.setVerticalHeaderItem(self.targets_table.rowCount()-1, QTableWidgetItem(row[0]))
                for col in range(4):
                    self.targets_table.setItem(self.targets_table.rowCount()-1, col, QTableWidgetItem(row[col+1]))


    def switch_protocol(self):
        '''
        Start or stop the protocol based on the current state of the switch_protocol_btn
        '''
        # two scenarios - either the protocol is already running, or it isn't
        if self.switch_protocol_btn.text() == 'Start protocol':
            # check if there are targets in the table; otherwise, don't start the protocol
            if self.targets_table.rowCount() == 0:
                # give a message
                ot.message('No targets in table')
                # unpress button
                self.switch_protocol_btn.setChecked(False)
                return
            # check if there are zero (control) groups, and if not, don't start the protocol
            groups = ot.get_groups(self.targets_table)
            unique_groups, _ = np.unique(groups, return_counts=True)
            if np.sum(groups == 0) == 0:
                # give a message
                ot.message('No control group in table')
                # unpress button
                self.switch_protocol_btn.setChecked(False)
                return
            # check if the are non-zero group values, and if not, don't start the protocol
            if np.sum(groups != 0) == 0:
                # give a message
                ot.message('No non-zero groups in table')
                # unpress button
                self.switch_protocol_btn.setChecked(False)
                return
            # check if there are non-cosecutive group values, and if so, don't start the protocol
            if np.sum(np.diff(np.sort(unique_groups)) != 1) != 0:
                # give a message
                ot.message('group values are not consecutive')
                # unpress button
                self.switch_protocol_btn.setChecked(False)
                return

            # if all of these conditions are met, then start the protocol
            # first, stop the task if it exists
            self.stop_task()
            # reset the ni card and then zero all while waiting
            ot.reset(self.NI_card.text(), self.cwd)


            # zero all while waiting
            self.zero_all()
            # if the protocol isn't running, start it
            self.switch_protocol_btn.setText('Stop protocol')
            # get protocol parameters
            output = ot.create_output(self)
            channels = f'{self.NI_card.text()}/ao{self.intensity_ch.value()}, \
                        {self.NI_card.text()}/ao{self.x_ch.value()}, \
                        {self.NI_card.text()}/ao{self.y_ch.value()}'
            sr = self.sample_rate.value()
            trigger = self.trigger_ch.text()
            stim_prob = self.stim_prob.value()
            # start the protocol process, with a pipe passing the last stimulated regions
            self.protocol = multiprocessing.Process(target=ot.start_protocol, args=(channels, sr, trigger, output, stim_prob, self.cwd))
            self.protocol.start()
        else:
            # if the protocol is running, stop it
            self.switch_protocol_btn.setText('Start protocol')
            # stop the protocol process
            self.protocol.terminate()
            # log last stimulation as none
            ot.log_last_stimulation('none', self.cwd)
            # return status to ready
            ot.log_status('Ready.', self.cwd)
            # reset ni card
            ot.reset(self.NI_card.text(), self.cwd)
            # wait 200 ms
            QtCore.QTimer.singleShot(200, self.zero_all)


    def update_status(self):
        '''
        Update the status according to the next stimulation log
        '''
        # periodically update the status according to the next stimulation log
        log_file = os.path.join(self.cwd, 'status.txt')
        # read the log_file
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                self.status.setTitle(line)

    def output_pulse(self):
        '''
        Output a pulse based on the current parameters
        '''
        # output a sine pulse
        self.stop_task()
        times = np.linspace(0, 1/self.stim_freq.value(), int(np.floor(self.sample_rate.value()/self.stim_freq.value())), endpoint=False)
        wave =  ot.create_stim(times, self.stim_freq.value(), self.sin_stim.isChecked(), self.duty_cycle.value())
        wave = wave*float(self.pulse_intensity.text())
        # extend the wave, which is currently one period, to the duration of the pulse, by tiling it by the number of periods in self.pulse_dur.value
        wave = np.tile(wave, int(self.pulse_dur.value()*self.stim_freq.value()/1000))
        # if include_taper is checked, taper the wave
        if self.include_taper.isChecked():
            taper_points = int(self.taper_dur.value()*self.sample_rate.value())
            wave[-taper_points:] = wave[-taper_points:]*np.linspace(1, 0, taper_points)
        ot.analog_out_pulse(self.NI_card.text(), self.intensity_ch.value(), self.sample_rate.value(), wave)
        # continue the ongoing intensity if there is one
        self.cur_intensity_changed()


    def zero_all(self):
        '''
        Zero all the values in the GUI
        '''
        self.stop_task()
        # set the current row to -1
        self.targets_table.setCurrentCell(-1, -1)
        # set all values to zero or empty
        self.protocol_intensity.setValue(0)
        self.x_val.setValue(0)
        self.y_val.setValue(0)
        self.target_name.setText('')
        self.target_group.setValue(0)
        # set current intensity to zero
        self.cur_intensity.setValue(0)
        self.cur_intensity_changed()


    def deleted_sel(self):
        '''
        Delete the selected row in the targets table
        '''
        # delete the selected row
        self.targets_table.removeRow(self.targets_table.currentRow())
        # set the current row to -1
        self.targets_table.setCurrentCell(-1, -1)


    def delete_all(self):
        '''
        Delete all rows in the targets table
        '''
        # delete all elements in the table
        self.targets_table.setRowCount(0)
        # set the current row to -1
        self.targets_table.setCurrentCell(-1, -1)


    def stop_task(self):
        '''
        Stop the task if it exists
        '''
        if hasattr(self, 'task'):
            self.task.stop()
            self.task.close()
            # delete the attribute
            del self.task

if __name__ == '__main__':
    app = QApplication(sys.argv)
    login_window = OptoTarget()
    sys.exit(app.exec())
    