:: Installing PYQUM 101 on WIN10 for DR-A

@echo off


rem Define here the path to your conda installation
set CONDAPATH=C:\Users\ASQUM_2\anaconda3
::C:\Users\ASQUM\anaconda3
::C:\ProgramData\Anaconda3
rem Define here the name of the environment
::set ENVNAME=base
set ENVNAME=PYQUM-server-offline

rem Activate the conda environment
rem Using call is required here, see: https://stackoverflow.com/questions/24678144/conda-environments-and-bat-files
ECHO Conda path: %CONDAPATH%\Scripts\activate.bat 
ECHO Environment name: %ENVNAME%
call %CONDAPATH%\Scripts\activate.bat %ENVNAME%


:: qspp (editable installation, files are in PYQUM)
ECHO Installing qspp
pip install -e ..\BETAsite\Signal_Processing

:: pulse_generator (editable installation, files are in PYQUM)
ECHO Installing pulse_generator
pip install -e ..\BETAsite\pulse_generator

:: asqpu (editable installation, files are in PYQUM)
ECHO Installing asqpu
pip install -e ..\BETAsite\asqpu

:: state_distinguishability (editable installation, files are in PYQUM)
ECHO Installing state_distinguishability
pip install -e ..\BETAsite\state_distinguishability

:: resonator_tools (editable installation, files are in PYQUM)
ECHO Installing resonator_tools
pip install -e ..\BETAsite\resonator_tools

:: atsapi (normal installation, files are in MEGA)
ECHO Installing atsapi
:: DR1 pip install ..\..\..\..\MEGAsync\MANUALS\DAC_ADC\AlazarTech\SDK\Library
pip install ..\..\..\..\MEGA\MANUALS\DAC_ADC\AlazarTech\SDK\Library

:: keysightSD1 (normal installation, files are in MEGA)
ECHO Installing keysightSD1
:: DR1 pip install ..\..\..\..\MEGAsync\MANUALS\DAC_ADC\KeySight\keysightSD1_3
pip install ..\..\..\..\MEGA\MANUALS\DAC_ADC\KeySight\keysightSD1_3

:: PYQUM (editable installation, files are in PYQUM)
ECHO Installing PYQUM 101
pip install -e .

PAUSE