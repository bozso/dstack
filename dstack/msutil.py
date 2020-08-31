"""
Collection of utility functions to interact with Measurement Sets
"""

__all__ = ['get_MS_phasecentre_all','get_single_phasecentre_from_MS','check_phaseref_in_MS',
            'get_N_chan_from_MS']

import numpy as np

from casacore import tables as casatables

from astropy.coordinates import SkyCoord
from astropy import units as u

def get_MS_phasecentre_all(mspath, frame='icrs', ack=False):
    """Get the list of the phase centres for each field and direction of the MS
    and return a list of astropy skycoord values

    Both field and direcrion IDs are expected to increment from zero, and the maximum
    ID can be the number of unique fields/dds. However, less than the maxumum number of
    valid IDs can occure and this code can handle that.

    e.g. one field and one direction ID, but in the PHASE_DIR table, 
    phase centre for two directions are existing, the code chooses the valid one

    Parameters
    ==========

    mspath: str
        The input MS path

    frame: str, optional
        Reference frame used to calculate the Astropy phase centre. Default: 'icrs'

    ack: bool, optional
        Enabling messages of successful interaction with the MS
        e.g. successful opening of a table
    
    Returns
    =======
    phasecentres: list of lists containing Astropy skycoords
        A list of the phasecentres for each field and direction in the MS as a list of lists
        i.e. each element is a list

    """
    MS = casatables.table(mspath, ack=ack)

    #Get the number of unique fields and data descriptoions (e.g. footprints)
    fields = np.unique(MS.getcol('FIELD_ID'))
    dds = np.unique(MS.getcol('DATA_DESC_ID'))

    fields_table = casatables.table(mspath + '/FIELD', ack=ack)    

    phasecentres = []

    #Get the reference equinox from the table keywords
    equinox = fields_table.getcolkeyword('PHASE_DIR','MEASINFO')['Ref'] 

    #Only can convert from radians
    assert fields_table.getcolkeyword('PHASE_DIR','QuantumUnits')[0] == 'rad', 'Phase centre direction is not in radians!'

    i = 0
    j = 0
    for field in range(0,np.size(fields)):
        #The number and referencing of fields can be messy
        if np.shape(fields_table.getcol('PHASE_DIR'))[1] > np.size(fields):
            field_ID = fields[i]
        else:
            field_ID = field

        directions = []

        for dd in range(0,np.size(dds)):
            #Same for the DDs as the fields
            if np.shape(fields_table.getcol('PHASE_DIR'))[0] > np.size(dds):
                dd_ID = dds[i]
            else:
                dd_ID = dd

            pc = fields_table.getcol('PHASE_DIR')[dd_ID,field_ID, :]

            #Convert to astropy coordinates
            directions.append(SkyCoord(ra=pc[0] * u.rad, dec=pc[1] * u.rad, frame=frame, equinox=equinox))

            j += 1
    
    phasecentres.append(directions)

    i += 1

    MS.close()

    return phasecentres

def get_single_phasecentre_from_MS(mspath, field_ID=0, dd_ID=0, frame='icrs', ack=False):
    """Get a given phase centre from the MS based on the field_ID and direction_ID

    Parameters
    ==========

    mspath: str
        The input MS path

    field_ID: int >= 0
        Field ID in the FIELD table. Note, that the FIELD_ID in the MAIN table can
        have a different value. e.g. FIELD_ID = 1, but only one filed exists, then the
        field_ID should be 0!

    dd_ID: int >= 0
        Direction ID in the FIELD table.

    frame: str, optional
        Reference frame used to calculate the Astropy phase centre. Default: 'icrs'

    ack: bool, optional
        Enabling messages of successful interaction with the MS
        e.g. successful opening of a table
    
    Returns
    =======
    phasecentre: Astropy coordinate 
        Phasecentre of the given field and direction
    """
    MS = casatables.table(mspath, ack=ack)

    fields_table = casatables.table(mspath + '/FIELD', ack=ack)    

    #Get the reference equinox from the table keywords
    equinox = fields_table.getcolkeyword('PHASE_DIR','MEASINFO')['Ref'] 

    #Only can convert from radians
    assert fields_table.getcolkeyword('PHASE_DIR','QuantumUnits')[0] == 'rad', 'Phase centre direction is not in radians!'

    pc = fields_table.getcol('PHASE_DIR')[dd_ID,field_ID, :]

    direction = SkyCoord(ra=pc[0] * u.rad, dec=pc[1] * u.rad, frame=frame, equinox=equinox)

    MS.close()

    return direction

def check_phaseref_in_MS(mspath, phaseref, sep_threshold=1., frame='icrs', ack=False):
    """Check if a given phasereference point is amongst the phase cntre of an MS for any
    firld and direction existing in that MS

    This function is needed as the Phase centre referencing is NOT clear in the MS format
    using ASKAP observations.

    Parameters
    ==========
    mspath: str
        The input MS path

    phaseref: Astropy coordinate
        Astropy SkyCoord object with the same frame as the :param frame: parameter 

    sep_threshold: float
        Maximum allowed separation between the given phaseref and the phasecentres in the MS.
        The separation is defined in arcesconds. If the phaseref and the phasecentre within the
        separation, it counts as a match

    frame: str, optional
        Reference frame used to calculate the Astropy phase centre. Default: 'icrs'

    ack: bool, optional
        Enabling messages of successful interaction with the MS
        e.g. successful opening of a table
    
    Returns
    =======
    IDs: list of lists
        If the phase reference given matches with at least one of the 
        phasecentre in the MS, the filed index and direction idex is returned as a list.
        Else an empty list is returned.

        The returned indices are the field folloved by direction for ecah match

    """
    assert type(phaseref) == type(SkyCoord(ra = 0 * u.deg, dec = 0 * u.deg, frame=frame, equinox='J2000')), 'Input phaseref is not an astropy SkyCoord object!'

    MS = casatables.table(mspath, ack=ack)

    fields_table = casatables.table(mspath + '/FIELD', ack=ack)    

    #Get the reference equinox from the table keywords
    equinox = fields_table.getcolkeyword('PHASE_DIR','MEASINFO')['Ref'] 

    #Only can convert from radians
    assert fields_table.getcolkeyword('PHASE_DIR','QuantumUnits')[0] == 'rad', 'Phase centre direction is not in radians!'

    IDs = []

    for d in range(0,np.shape(fields_table.getcol('PHASE_DIR'))[0]):
        for f in range(0,np.shape(fields_table.getcol('PHASE_DIR'))[1]):
            pc = fields_table.getcol('PHASE_DIR')[d,f, :]

            if phaseref.separation(SkyCoord(ra=pc[0] * u.rad, dec=pc[1] * u.rad, frame=frame, equinox=equinox)).arcsecond <= sep_threshold:
                IDs.append([f,d])

    MS.close()

    return IDs

def get_N_chan_from_MS(mspath, ack=False):
    """Get the number of channels from an MS

    Parameters
    ==========
    mspath: str
        The input MS path

    ack: bool, optional
        Enabling messages of successful interaction with the MS
        e.g. successful opening of a table
    
    Returns
    =======
    N_chan: int
        Number of channels in the MS
    """
    MS = casatables.table(mspath, ack=ack)

    spectral_windows_table = casatables.table(mspath + '/SPECTRAL_WINDOW', ack=ack)

    #Select firts index, channels can be different for different fields and dds maybe
    N_chan = spectral_windows_table.getcol('NUM_CHAN')[0]

    MS.close()

    return N_chan



if __name__ == "__main__":
    MSPATH = '/home/krozgonyi/Desktop/sandbox/scienceData_SB10991_G23_T0_B_06.beam17_SL_C_100_110.ms'

    PHASEREF = SkyCoord(ra=5.9706226 * u.rad, dec= -0.5708741 * u.rad, frame='icrs', equinox='J2000')


    get_N_chan_from_MS(MSPATH)

    exit()