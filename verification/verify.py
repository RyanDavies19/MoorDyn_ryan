import ctypes
import os
import numpy as np
import matplotlib.pyplot as plt

def f_compile(run_files = []):

    # run_files is a list of file names to skip deleting when cleaning up from compiling MDF

    # Compile MoorDyn_Driver from OpenFAST.
    ### Alternatively this can be compiled externally and the path to moordyn_driver provided in the self.f_build() function
    OpenFAST_path = '../../MoorDynF' # FIXME: Path to OpenFAST top directory
    os.system(f'cmake {OpenFAST_path}')
    os.system('make moordyn_driver')
    os.system('mv modules/moordyn/moordyn_driver ./')
    for file in os.listdir('./'):
        if ((file != 'moordyn_driver') and not ('.py' in file) and (file not in run_files) and (file not in 'ptfm_motions.dat')):
            # remove everything except driver executable, this script, test file, and ptfm_motions
            os.system(f'rm -rf {file}')

def read_mooring_file(fileName):
    # Taken from MoorPy: https://github.com/NREL/MoorPy
    # load MD data from time series
        
    f = open(fileName, 'r')
    
    channels = []
    units = []
    data = []
    i=0
    
    printed = False # Handling fortran output error where near 0 values are ***
    for line in f:          # loop through lines in file
        if len(line.split()) > 1 and ('predictions were generated by MoorDyn' not in line): # skip blank lines
            if (i == 0):
                for entry in line.split():      # loop over the elemets, split by whitespace
                    channels.append(entry)      # append to the last element of the list
            elif (i == 1):
                for entry in line.split():      # loop over the elemets, split by whitespace
                    units.append(entry)         # append to the last element of the list

            elif len(line.split()) > 0:
        
                data.append([])  # add a new sublist to the data matrix
                import re
                r = re.compile(r"(?<=\d)\-(?=\d)")  # catch any instances where a large negative exponent has been written with the "E"
                line2 = r.sub("E-",line)            # and add in the E
                
                for entry in line2.split():      # loop over the elemets, split by whitespace
                    if '***' in entry:
                        if printed == False:
                            printed = True
                        entry = 0.0   
                    data[-1].append(entry)      # append to the last element of the list
                
            else:
                break
        
            i+=1
    
    f.close()  # close data file
    
    # use a dictionary for convenient access of channel columns (eg. data[t][ch['PtfmPitch'] )
    ch = dict(zip(channels, range(len(channels))))
    
    data2 = np.array(data)
    
    data3 = data2.astype(float)

    return data3, ch, channels, units 

def passing_channels(test, baseline, RTOL_MAGNITUDE = 2.0, ATOL_MAGNITUDE = 1.9) -> np.ndarray:

    # Taken from OpenFAST reg tests: https://github.com/OpenFAST/openfast/blob/main/reg_tests/lib/pass_fail.py

    """
    test, baseline: arrays containing the results from OpenFAST in the following format
        [
            channels,
            data
        ]
    So that test[0,:] are the data for the 0th channel and test[:,0] are the 0th entry in each channel.

    rtol: relative tolerance magnitude. Default value from OpenFAST defaults
    atol: absolute tolerance magnitude. Default value from OpenFAST defaults
    """

    NUMEPS = 1e-12
    ATOL_MIN = 1e-6

    where_close = np.zeros_like(test, dtype=bool)

    if test.size != baseline.size:
        passing_channels = np.all(where_close, axis=1) # all false
        return passing_channels

    n_channels = np.shape(test)[0]

    rtol = 10**(-1 * RTOL_MAGNITUDE)
    for i in range(n_channels):
        baseline_offset = baseline[i] - np.min(baseline[i])
        b_order_of_magnitude = np.floor( np.log10( baseline_offset + NUMEPS ) )
        atol = 10**(max(b_order_of_magnitude) - ATOL_MAGNITUDE)
        atol = max(atol, ATOL_MIN)
        where_close[i] = np.isclose( test[i], baseline[i], atol=atol, rtol=rtol )

    where_not_nan = ~np.isnan(test)
    where_not_inf = ~np.isinf(test)

    passing_channels = np.all(where_close * where_not_nan * where_not_inf, axis=1)
    return passing_channels


class Line(): # from MoorPy: https://github.com/NREL/MoorPy
    '''A class for any mooring line that consists of a single material'''
    def __init__(self, num, isRod=0, coupled = 0, rA = np.zeros(3), rB = np.zeros(3)):
        '''Initialize Line attributes
        Parameters
        ----------
        num : int
            indentifier number
        lineType : dict
            dictionary containing the coefficients needed to describe the line (could reference an entry of System.lineTypes).
        isRod : boolean, optional
            determines whether the line is a rod or not. The default is 0.
        coupled : int
            coupled or free rod
        rA : vec3
            rod end A coordinates
        rB : vec3
            rod end B coordinates
        Returns
        -------
        None.
        '''
                
        self.number = num
        self.isRod = isRod
                
        self.coupled = coupled # useful for determining state vector w/ coupled rod
                    
        self.rA = rA # end coordinates for rods
        self.rB = rB

class Body(): # from MoorPy: https://github.com/NREL/MoorPy
    '''A class for any object in the mooring system that will have its own reference frame'''
    
    def __init__(self, num, type, r6):
        '''Initialize Body attributes

        Parameters
        ----------
        num : int
            indentifier number
        type : int
            the body type: 0 free to move, 1 fixed, -1 coupled externally
        r6 : array
            6DOF position and orientation vector [m, rad]
        
        Returns
        -------
        None.

        '''
    
        self.number = num
        self.type   = type                          # 0 free to move, or -1 coupled externally
        self.r6     = np.array(r6, dtype=np.float_)     # 6DOF position and orientation vector [m, rad]

class Point():  # from MoorPy: https://github.com/NREL/MoorPy
    '''A class for any object in the mooring system that can be described by three translational coorindates'''
    
    def __init__(self, num, type, r):
        '''Initialize Point attributes

        Parameters
        ----------
        num : int
            indentifier number
        type : int
            the point type: 0 free to move, 1 fixed, -1 coupled externally
        r : array
            x,y,z coorindate position vector [m].
        
        Returns
        -------
        None.

        '''

        self.number = num
        self.type = type                # 1: fixed/attached to something, 0 free to move, or -1 coupled externally
        self.r = np.array(r, dtype=np.float_)
 
class load_inout():

    # Built from MoorPy system class: https://github.com/NREL/MoorPy
    def __init__(self, rootname = "", extension = "", tMax = 0):
        
        # MD input file name stuff
        self.rootname = rootname
        self.extension = extension
        self.in_file = str(rootname+extension)

        self.MDoptions = {} # dictionary that can hold any MoorDyn options read in from an input file, so they can be saved in a new MD file if need be

        self.tMax = tMax # length of simulation

        # read in data from an input file if a filename was provided
        if len(self.in_file) > 0:
            self.load()

    def load(self):  # from MoorPy: https://github.com/NREL/MoorPy
        '''Loads a MoorPy System from a MoorDyn-style input file

        Parameters
        ----------
        filename : string
            the file name of a MoorDyn-style input file.

        Returns
        -------
        None.

        '''
        
        # create/empty the lists to start with

        # ensure the mooring system's object lists are empty before adding to them
        self.bodyList = []
        self.rodList  = []
        self.pointList= []
        
        # number of coupled objects, for determining vector size in running MoorDyn
        self.num_coupled = 0 
        
        # assuming normal form
        f = open(self.in_file, 'r')

        # read in the data
        for line in f:          # loop through each line in the file

            # get properties of each Body
            if line.count('---') > 0 and (line.upper().count('BODIES') > 0 or line.upper().count('BODY LIST') > 0 or line.upper().count('BODY PROPERTIES') > 0):
                line = next(f) # skip this header line, plus channel names and units lines
                line = next(f)
                line = next(f)
                while line.count('---') == 0:
                    entries = line.split()  # entries: ID   Attachment  X0  Y0  Z0  r0  p0  y0    M  CG*  I*    V  CdA*  Ca*            
                    num = int(entries[0])
                    entry0 = entries[1].lower()                         
                    
                    if ("fair" in entry0) or ("coupled" in entry0) or ("ves" in entry0):       # coupled case
                        self.num_coupled += 1
                        bodyType = -1                        
                    
                        r6  = np.array(entries[2:8], dtype=float)   # initial position and orientation [m, rad]
                        r6[3:] = r6[3:]*np.pi/180.0                 # convert from deg to rad
                                                                
                        # add the body
                        self.bodyList.append(Body(num, bodyType, r6) )
                                
                    line = next(f)
                    
            # get properties of each rod
            if line.count('---') > 0 and (line.upper().count('RODS') > 0 or line.upper().count('ROD LIST') > 0 or line.upper().count('ROD PROPERTIES') > 0):
                line = next(f) # skip this header line, plus channel names and units lines
                line = next(f)
                line = next(f)
                while line.count('---') == 0:
                    entries = line.split()  # entries: RodID  RodType  Attachment  Xa   Ya   Za   Xb   Yb   Zb  NumSegs  Flags/Outputs
                    num = int(entries[0])
                    attachment = entries[2].lower()
                    if ('coupled' in attachment) or ('Coupled' in attachment) or ('vessel' in attachment) or ('Vessel' in attachment):
                        self.num_coupled += 1
                        coupled = 1
                    
                        rA = np.array(entries[3:6], dtype=float)
                        rB = np.array(entries[6:9], dtype=float)
                    
                        self.rodList.append(Line(num, isRod=1, coupled=coupled, rA = rA, rB = rB) )
                        
                    line = next(f)
                    
            # get properties of each Point
            if line.count('---') > 0 and (line.upper().count('POINTS') > 0 or line.upper().count('POINT LIST') > 0 or line.upper().count('POINT PROPERTIES') > 0 or line.upper().count('CONNECTION PROPERTIES') > 0 or line.upper().count('NODE PROPERTIES') > 0):
                line = next(f) # skip this header line, plus channel names and units lines
                line = next(f)
                line = next(f)
                while line.count('---') == 0:
                    entries = line.split()         # entries:  ID   Attachment  X       Y     Z      Mass   Volume  CdA    Ca
                    entry0 = entries[0].lower()          
                    entry1 = entries[1].lower() 
                    
                    num = np.int_("".join(c for c in entry0 if not c.isalpha()))  # remove alpha characters to identify Point #
                        
                    if ("fair" in entry1) or ("ves" in entry1) or ("couple" in entry1):
                        # for coupled point type, just set it up that same way in MoorPy (attachment to a body not needed, right?)
                        pointType = -1     
                        self.num_coupled += 1                       
                       
                        r = np.array(entries[2:5], dtype=float)
                        self.pointList.append(Point(num, pointType, r))

                    line = next(f)
                    
            # get options entries
            if line.count('---') > 0 and "options" in line.lower():
                line = next(f) # skip this header line
                
                while line.count('---') == 0:
                    entries = line.split()       
                    entry0 = entries[0] #.lower() 
                    entry1 = entries[1] #.lower() 
                    
                    # also store a dict of all parameters that can be regurgitated during an unload
                    self.MDoptions[entry1] = entry0
                    
                    line = next(f)

        f.close()  # close data file

    def compare(self, tMax = 0):
        
        # compare MDF and MDC outputs

        # plot main output channels for comparison 
        plot_channels = True # true for testing

        # paramters from MD input file
        self.tMax = int(tMax) # redundant
        self.dtM = float(self.MDoptions['dtM'])
        self.dtOut = float(self.MDoptions.get('dtOut', self.dtM))
        self.plot_tRange = (0,self.tMax-1)
        self.out_dirname = './'

        # Read main MoorDyn output files
        dataF, self.chF, self.channelsF, self.unitsF = read_mooring_file(self.out_dirname+self.rootname+'F'+'.out')
        dataC, self.chC, self.channelsC, self.unitsC = read_mooring_file(self.out_dirname+self.rootname+'C'+'.out')

        # Fix non uniform dtout timesteps
        if len(dataF[:,0]) != (self.tMax/self.dtOut) - 1:
            self.dataF = self.dtOut_fix(dataF, len(self.channelsF))
        else: 
            self.dataF = dataF
        if len(dataC[:,0]) != (self.tMax/self.dtOut) - 1:
            self.dataC = self.dtOut_fix(dataC, len(self.channelsC))
        else: 
            self.dataC = dataC

        # plot main output channels for comparison 
        if plot_channels: 

            if (len(self.channelsF) != len(self.channelsC)):
                print('ERROR: Different output channels in main .out files between F and C')
                exit(1) # could have better error handling

            if len(self.channelsF) > 2:
                fig, ax = plt.subplots(len(self.channelsF)-1, 1, sharex=True)
            else:
                fig, ax = plt.subplots(1,1)

            if len(self.channelsF) > 2:
                for k, channel in enumerate(self.channelsF):
                    if k != 0:
                        self.plot_channel(ax[k-1], channelnum = k)
            else:
                self.plot_channel(ax, channelnum = 1)

            # FIXME: Do we want to plot outputs, if so can GH actions save it for download?

            fig.suptitle(self.rootname+': Output channels')
            if len(self.channelsF) > 2:
                for k, channel in enumerate(self.channelsF):
                    if k != 0:
                        ax[k-1].legend(['C','F'], loc = 1)
                        ax[k-1].set_ylabel(channel+' '+self.unitsF[k])
                        ax[k-1].set_xlim(self.plot_tRange)
                    if k == len(self.channelsF):
                        ax[k-1].set_xlabel('Time (s)')
            else: 
                ax.legend(['C','F'], loc = 1)
                ax.set_ylabel(self.channelsF[1]+' '+self.unitsF[1])
                ax.set_xlim(self.plot_tRange)
                ax.set_xlabel('Time (s)')
            fig.tight_layout()
            fig.savefig(self.rootname+'_chan.png', dpi = 300)


        # compare output lists. TODO: test

        rtol = 2.0 # relative tolerance magnitude
        atol = 1.9 # absolute tolerance magnitude
        passing = passing_channels(self.dataC.T, self.dataF.T, rtol, atol)
        passing = passing.T
        
        # passing case
        if np.all(passing):
            print("Passed!")
        else:
            print("Failed.")

        plt.show()


    def dtOut_fix (self, data, num_channels, tdata = None):

        # fixes non uniform output time steps

        time = np.arange(self.dtOut, self.tMax, self.dtOut)
        if num_channels == 1:
            data1 = np.zeros(len(time))
            if tdata is None:
                print('ERROR: no time data for dtOut fix')
                exit(1)
            else:
                for i in range(1,num_channels):
                    data1[i] = np.interp(time, tdata, data[i])
        else: 
            data1 = np.zeros((len(time), num_channels))
            if tdata is None:
                data1[:,0] = time
                for i in range(1,num_channels):
                    data1[:,i] = np.interp(time, data[:,0], data[:,i])
            else:
                for i in range(0,num_channels):
                    data1[:,i] = np.interp(time, tdata, data[:,i])
        return data1 

    def plot_channel(self, ax, channelnum = 1):
        
        min = np.where(self.dataF.astype(int)[:,0]==self.plot_tRange[0])[0][0] # this is a slow process
        max = np.where(self.dataF.astype(int)[:,0]==self.plot_tRange[1])[0][0]

        ax.plot(self.dataF[min:max,0], self.dataF[min:max,channelnum], color = 'b', linestyle = "-")
        ax.plot(self.dataC[min:max,0], self.dataC[min:max,channelnum], color = 'r', linestyle = "--")

class run_infile():

    def __init__(self, dynamics_args = {}):
        self.dynamics_args = dynamics_args
            
    def load_dynamics(self):

        # load array of state vectors for calls to MD step

        static = self.dynamics_args.get('static', False)
        from_file = self.dynamics_args.get('from_file', False)

        # initializing
        self.time = np.arange(0, self.tMax, self.dtC)
        size = (len(self.time), self.vector_size)
        self.x = np.zeros(size, dtype = float)
        self.xd = np.zeros(size, dtype = float)
        if static:
            self.xdp = np.zeros(size)
            self.xp = np.zeros(size)
            for i in range(len(self.time)):
                self.x[i,:] = self.xi

        elif from_file:
            self.get_positions()
            for i in range(len(self.time)):
                if i == 0:
                    self.x[i,:] = self.xi
                else:
                    j = 0
                    while j < self.vector_size:
                        self.x[i,j:j+self.dof] = self.x[i-1,j:j+self.dof] + self.xdp[i, j:j+self.dof] * self.dtC
                        self.xd[i,j:j+self.dof] = self.xdp[i, j:j+self.dof]
                        j += self.dof

        # Specifying correct dtypes for conversion to C
        self.xi = np.array(self.xi, dtype = float) 
        self.x = np.array(self.x, dtype = float)
        self.xd = np.array(self.xd, dtype = float)
    
    def get_positions(self):

        # load in coupled motion from file for use with MD-C

        exciteFileName = "ptfm_motions.dat" # rotation deg of freedom need to be in radians
        i=0  # file line number
        t_in = []
        Xp_in = []   
        with open(exciteFileName, 'r') as myfile2: # open an input stream to the line data input file
            for line2 in myfile2:

                #  split line by tabs
                datarow = list(line2.split())
                
                if ((len(datarow) < 7) and (self.dof == 6)): 
                    print("MD_Driver: Seems like we've hit a bad line or end of file. ")
                    break;                  # break if we're on a last empty line
                if ((len(datarow) < 4) and (self.dof == 3)): 
                    print("MD_Driver: Seems like we've hit a bad line or end of file. ")
                    break;                  # break if we're on a last empty line
                
                t_in.append(float(datarow[0]))
                scaled_data = []			
                for j in range(self.dof*self.num_coupled):
                    scaled_data.append(float(datarow[j+1])) # add platform positions
                Xp_in.append(scaled_data)
                i += 1

        myfile2.close()

        Xp_in = np.array(Xp_in)

        # interpolator for platform positions: t_in is vector of time steps from position input file. xp_in is dof
        ts = 0
        self.xp = np.zeros((len(self.time),len(Xp_in[0])))
        for its in range(0, len(self.time)):

            t = its*self.dtC
            
            # interpolate platform positions from file data, and approximate velocities
            while ts < (len(t_in)-1):  # search through platform motion data time steps (from .out file)	
                if (t_in[ts+1] > t):				
                    frac = ( t - t_in[ts] )/( t_in[ts+1] - t_in[ts] )		# get interpolation fraction
                    for j in range(0, len(Xp_in[0])):
                        self.xp[its][j] = Xp_in[ts][j] + frac*( Xp_in[ts+1][j] - Xp_in[ts][j] ) # interpolate for each platform DOF
                    break
                ts += 1
        self.xdp = np.zeros((len(self.time),len(Xp_in[0])))
        xold = np.zeros(len(Xp_in[0]))
        # calculate velocities using finite difference
        for i in range(len(self.time)):
            self.xdp [i] = (self.xp[i] - xold)/self.dtC
            xold =  self.xp[i]
        
        return
    
    def f_build(self):

        # Build MDF driver input file. Formatted according to moordyn.readthedocs.io

        driverfile = "MoorDyn.dvr"

        if self.num_coupled == 0:
            InputsMode = 0
        else:
            InputsMode = 1
        
        with open(driverfile, 'w') as myfile:     # open an input stream to the line data input file
            myfile.writelines(['MoorDyn driver input file \n'])
            myfile.writelines(['another comment line\n'])
            myfile.writelines(['---------------------- ENVIRONMENTAL CONDITIONS ------------------------------- \n'])
            myfile.writelines(['9.80665            Gravity          - Gravity (m/s^2) \n'])
            myfile.writelines(['{}             rhoW             - Water density (kg/m^3) \n'.format(self.WtrDnsty)])
            myfile.writelines(['{}              WtrDpth          - Water depth (m) \n'.format(self.WtrDpth)])
            myfile.writelines(['---------------------- MOORDYN ------------------------------------------------ \n'])
            myfile.writelines(['"{}"      MDInputFile      - Primary MoorDyn input file name (quoted string) \n'.format(os.path.abspath(self.file))])
            myfile.writelines(['"F"            OutRootName      - The name which prefixes all HydroDyn generated files (quoted string) \n'])
            myfile.writelines(['{}                  TMax             - Number of time steps in the simulations (-) \n'.format(self.tMax)])
            myfile.writelines(['{}                 dtC              - TimeInterval for the simulation (sec) \n'.format(self.dtC)])
            myfile.writelines(['{}                   InputsMode       - MoorDyn coupled object inputs (0: all inputs are zero for every timestep (no coupled objects), 1: time-series inputs (coupled objects)) (switch) \n'.format(InputsMode)])
            myfile.writelines(['"ptfm_motions.dat"   InputsFile       - Filename for the MoorDyn inputs file for when InputsMod = 1 (quoted string) \n'])
            myfile.writelines(['0                   NumTurbines      - Number of wind turbines (-) [>=1 to use FAST.Farm mode. 0 to use OpenFAST mode.] \n'])
            myfile.writelines(['---------------------- Initial Positions -------------------------------------- \n'])
            myfile.writelines(['ref_X    ref_Y    surge_init   sway_init  heave_init  roll_init  pitch_init   yaw_init \n'])
            myfile.writelines(['(m)      (m)        (m)          (m)        (m)       (rad)       (rad)        (rad)         [followed by MAX(1,NumTurbines) rows of data] \n'])
            myfile.writelines(['0         0          0            0          0          0           0            0 \n'])
            myfile.writelines(['END of driver input file \n'])

    def run_f(self):

        # Runs the MoorDyn-F driver
        ### This runs until self.Tmax, using same coupling step sent to MD-C
        ### For coupled simulations, MD-F uses the PtfmMotions file written above
        os.system(f"./moordyn_driver MoorDyn.dvr")

        # standardizing output file names
        files = os.listdir('./')
        for file in files:
            components = file.split('.')
            if ('MD' in components) and ('F'in components):
                components.remove('MD')
                components.remove('F')
                if len(components) == 1:
                    new_name = self.rootname+'F.'+ components[0]
                else:
                    new_name = self.rootname+'F_'+ ('.'.join(map(str, components)))
                os.system('mv {} {}'.format(file, new_name)) 

    def run_c (self): 
      
        # also option to do this with the python code. I have the code to do that but didn't include for simplicity

        # -------------------- load the MoorDyn DLL ---------------------

        #Double vector pointer data type
        double_p = ctypes.POINTER(ctypes.c_double)

        # Make MoorDyn function prototypes and parameter lists (remember, first entry is return type, rest are args)
        MDInitProto = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_double*self.vector_size), ctypes.POINTER(ctypes.c_double*self.vector_size), ctypes.c_char_p) #need to add filename option here, maybe this c_char works? #need to determine char size 
        MDStepProto = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_double*self.vector_size), ctypes.POINTER(ctypes.c_double*self.vector_size), ctypes.POINTER(ctypes.c_double*self.vector_size), double_p, double_p)
        MDClosProto = ctypes.CFUNCTYPE(ctypes.c_int)

        MDInitParams = (1, "x"), (1, "xd"), (1, "infilename") 
        MDStepParams = (1, "x"), (1, "xd"), (2, "f"), (1, "t"), (1, "dtC") 

        # lib_path = '../build/source/libmoordyn.dylib'# FIXME: Fix if needed: path to MD-C compiled library. 
        lib_path = '../compile/DYLIB/libmoordyn2.dylib' #CMake is not currently working for me (Ryan) on most recent dev branch, so using  old method

        MDlib = ctypes.CDLL(lib_path) #load moordyn dylib

        MDInit = MDInitProto(("MoorDynInit", MDlib), MDInitParams)
        MDStep = MDStepProto(("MoorDynStep", MDlib), MDStepParams)
        MDClose= MDClosProto(("MoorDynClose", MDlib))  
        # ------------------------ run MoorDyn ---------------------------
        # initialize some arrays for communicating with MoorDyn
        t  = double_p()    # pointer to t

        # parameters
        dtC = ctypes.pointer(ctypes.c_double(self.dtC))

        infile = ctypes.c_char_p(bytes(self.file, encoding='utf8'))

        # initialize MoorDyn at origin
        MDInit((self.x[0,:]).ctypes.data_as(ctypes.POINTER(ctypes.c_double*self.vector_size)),(self.xd[0,:]).ctypes.data_as(ctypes.POINTER(ctypes.c_double*self.vector_size)),infile)

        # loop through coupling time steps
        for i in range(len(self.time)):
            t = ctypes.pointer(ctypes.c_double(self.time[i]))
            MDStep((self.x[i,:]).ctypes.data_as(ctypes.POINTER(ctypes.c_double*self.vector_size)), (self.xd[i,:]).ctypes.data_as(ctypes.POINTER(ctypes.c_double*self.vector_size)), t, dtC)    
        # close MoorDyn simulation (clean up the internal memory, hopefully) when finished
        MDClose()   

        del MDlib

        out_file = self.rootname+'.out'
        new_file = self.rootname+'C'+'.out'
        os.system(f'cp {out_file} {new_file}') # rename file for reading in comparison

    def run_comparison(self, run_args = {}):

        self.rootname = run_args.get('rootname', 'lines')
        self.extension = run_args.get('extension', '.txt')
        self.file = self.rootname+self.extension
        self.tMax = run_args.get('tMax', 60)
        self.dof = run_args.get('dof', 3)

        #------------------- Set up Mooring line conditions -----------------------------

        
        inputs = load_inout(rootname = self.rootname, extension = self.extension, tMax = self.tMax)

        # parameters from MDoptions dict
        self.dtC = float(inputs.MDoptions["dtM"])
        self.WtrDnsty = float(inputs.MDoptions.get('WtrDnsty', 1025.0))
        self.WtrDpth = float(inputs.MDoptions['WtrDpth'])
        self.num_coupled = inputs.num_coupled

        # Inital fairlead locations
        ### NOTE: This only works is all coupled objects are either points or bodies/rods (all coupled need to have same # of DOF's)
        self.vector_size = int(inputs.num_coupled*self.dof)
        self.xi = np.zeros(self.vector_size)
        i = 0
        if self.dof == 3:
            for point in inputs.pointList:
                if point.type == -1:  
                    self.xi[i]=(point.r[0])
                    self.xi[i+1]=(point.r[1])
                    self.xi[i+2]=(point.r[2])
                    i += self.dof
        if self.dof == 6 :
            for body in inputs.bodyList:
                if body.type == -1:  
                    self.xi[i]=(body.r6[0])
                    self.xi[i+1]=(body.r6[1])
                    self.xi[i+2]=(body.r6[2])
                    self.xi[i+3]=(body.r6[3])
                    self.xi[i+4]=(body.r6[4])
                    self.xi[i+5]=(body.r6[5])
                    i += self.dof
            for rod in inputs.rodList:
                if rod.coupled == 1:  
                    self.xi[i]=(rod.rA[0])
                    self.xi[i+1]=(rod.rA[1])
                    self.xi[i+2]=(rod.rA[2])
                    self.xi[i+3]=0
                    self.xi[i+4]=np.pi
                    self.xi[i+5]=0
                    i += self.dof

        # Call functions and run both versions

        self.load_dynamics()

        self.f_build()

        self.run_f() 

        self.run_c()
            
        inputs.compare(tMax = self.tMax)


# FIXME: Does GH actions automatically delete the MD output files? If not then we need to handle that here

# NOTE: @Pepe the FIXME's are where paths will need to be adjusted from what they are locally for me, and if we want to save figures/out files. 

# NOTE: @Pepe I used os.system() with Unix scripts for file handling and calling the driver. I can change to generalize for all OS but this was easier for now.

# NOTE: MD-F will throw warnings if it doesn't recognize things from the options section that are in MD-C. WtrDnsty is automaticaaly added into the driver input file with this script. The docs lists the differences between the options lists in MD-sC and MD-F 


if __name__ == "__main__":
   
    #------------------- Run All Scripts -----------------------------

    # Required
    dynamics_args = {'static' : False, 
                     'from_file' : True, 
                     }
    ### ptfm_motions.dat can be provided to give coupled platform motion


    # Required
    run_args = {'rootname' : 'vertical_spar',
                'extension' : '.dat', 
                'tMax' : 15,  # simulation duration (s)
                'dof' : 6, # DOF of coupled objects: 3 DOF for lines, points, connections, 6 DOF for bodies and rods (for no coupled objects, set to 3). TODO: make this work for coupled bodies and rods at the same time
                } 

    # this compiles MDF, after which as many runs of comparison files can be done
    ### run_files is a list of all files that should not be deleted when cleaning up from compiling
    f_compile(run_files=[run_args['rootname']+run_args['extension']])

    instance = run_infile(dynamics_args = dynamics_args) 
    instance.run_comparison(run_args = run_args)