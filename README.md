<div align="center">
<video src="https://github.com/msokolet/optotarget/assets/a3e691ca-4ea4-47e1-bd31-e38892cbefaa" width="400" autoplay loop>
</div>

## OptoTarget

GUI for running optogenetic stimulation protocols across multiple targets using X and Y galvanometers. The original approach is based on [Guo et al. 2014](https://pubmed.ncbi.nlm.nih.gov/24361077/), but is different in two main ways: first, this package has the ability to stimulate several regions simulatenously (most importantly across the two hemispheres), and second, targets are defined manually and not necessarily in a grid-like pattern. While a grid-like pattern may be useful for some exploratory projects, for many other projects it may be better to identify potentially important targets using apriori knowledge or neural activity recordings, which will greatly lower the number of trials needed for reasonable statistical power.

Requirements:
1. A laser device with intensity controllable by an analog input
2. X and Y galvometric mirrors that deflect the laser beam, with their positions controllable by analog inputs
3. An NI card with at least 3 analog outputs and a trigger (TTL) input
4. An installation of [NI-DAQmx](https://www.ni.com/en/support/downloads/drivers/download.ni-daq-mx.html)
5. (Highly recommended) A camera, to target the laser beam.

First run only:
1. Install an [Anaconda](https://www.anaconda.com/download/) distribution of Python.
2. Download or clone this package.
3. Open Anaconda Prompt.
4. Change directory to the package folder with `cd optotarget`
5. Create the optotarget environment with `conda env create -f environment.yml`
6. Run `python optotarget.py`

Subsequent runs:
1. Open Anaconda Prompt.
2. Change directory to the package folder with `cd optotarget`
3. Run `conda activate optotarget`
4. Run `python optotarget.py`

Instructions:
1. Select the stimulation parameters (hover over each parameter for an explanation).
2. Use the slider in step 2 to test these parameters as well as various intensities online, and optionally to produce a test pulse. Note the X and Y sliders in step 3 also control the online X and Y position.
3. Create new targets using "create new" or load them from file via "load all". For each target, set the intensity, X position, and Y position, and group. The group determines which targets are activated together, with group 0 being the control group.
4. Press 'start protocol'.

How it works:
After pressing 'start protocol', the program waits for a trigger (TTL) pulse in the specified trigger channel. Each time it receives a pulse, it generates a psuedorandom number between 0 and 100. If the number is greater than 'stimulus probability', then group 0 (control) targets are stimulated. If it is lower than 'stimulus probability', then non-group 0 targets are stimulated, with each group being equally likely to be chosen. The status (upcoming targets) is saved in 'status.txt', the most recent targets are saved in 'stim.txt', and a continuous log of all targets is saved in 'log.txt'.

At the top you can see an example of OptoTarget in action. Note this visualization requires a separate program to see the cortex and map it to the Allen Mouse Brain Common Coordinate Framework (for instance, [wfield](https://github.com/jcouto/wfield) by João Couto).

