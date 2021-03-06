"""
Collection of functions operating on images in CASAImageformat.
The functions defined here are expected to work on grids as well, as grids are currently dumped in casaimage format,
hence functions defined in this module works on both images and grids.
The image I/O management is kinda manually at this point, but hopefully will be handled on higher level applications in the future.
"""

__all__ = ['create_CIM_object', 'get_N_chan_from_CIM', 'get_N_pol_from_CIM',
            'measure_CIM_RMS', 'check_CIM_equity', 'check_CIM_coordinate_equity', 
            'create_CIM_diff_array', 'CIM_stacking_base']

import os
import shutil
import numpy as np
import warnings

from casacore import images as casaimage
from casacore import tables as casatables

import dstack as ds

def create_CIM_object(cimpath):
    """This function aims to speed up other bits of this and ``cgrid``
    modules, by returning a ``casacore.images.image.image`` object.

    The trick is, that the ``cimpath`` argument can be either a string i.e. the path
    to the CASAImage wich will be read in and returned, **or** it can be already an
    in-memory ``casacore.images.image.image`` object.

    This might not be the best solution, but I hope overall a check in a lot of cases will
    speed up code, rather than reading in the same CASAImage again-and again. So ideally, only
    one reading in happens for each CASAImage and all inside this function!

    Parameters
    ==========
    cimpath: str
        The input CASAImage path or a ``casacore.images.image.image`` object

    Returns
    =======
    cim: ``casacore.images.image.image`` object
        The in-memory CASAImage

    """
    #create an empty image in-memory to check the object type
    #if type(cimpath) == type(casaimage.image(imagename='',shape=np.ones(1))):
    if type(cimpath) == 'casacore.images.image.image':
        return cimpath
    else:
        # We could simply return, no need to assign the return value of
        # `casaimage.image(cimpath)` to a new variable.
        return casaimage.image(cimpath)

def check_axes(cim, required_axes=4):
    """Checks if the ``cim`` image object has the correct number of
    axes or dimensions. Raises
    
    Notes
    =====
    I would refactor this safety check into this separate function, even
    though it is only used in two functions. Couple of reasons:
    
    If later it is decided that a different number of axes needs
    to be used, this function can simply be updated so that
    ``required_axes`` will have a different default value and there will
    be no need to copy and paste changes in different parts of the code.
    
    This function can be used in different modules if the need arises,
    and there will be no need to copy-paste the code segment.
    
    Parameters
    ==========
    cim: ``casacore.images.image.image`` object
        In-memory CASAImage
    required_axes: int
        Number of required axes or dimensions for the ``cim`` image
        object.
    
    Raises
    ======
    AssertionError
        If the number of axes is does not equal the required
        numbers.
    """
    assert cim.ndim() == required_axes, 'The image has more than 4 axes!'
    

# one space should follow each comma (,)
def get_N_chan_from_CIM(cimpath, close=False):
    """Get the number of channels from a CASAImage

    CASAImage indices: [freq, Stokes, x, y]

    Parameters
    ==========
    cimpath: str
        The input CASAImage path or a ``casacore.images.image.image`` object
    
    close: bool, optional
        If True the in-memory CASAIMage is deleted, and the optional write-lock releases
        Set to true if this is the last operation on the image, but False if other functions
        called that operation on the same image. This avoids multiple read-in of the image.

    Returns
    =======
    N_chan: int
        Number of channels in the CASAImage
    """
    cim = ds.cim.create_CIM_object(cimpath)
    assert cim.ndim() == 4, 'The image has more than 4 axes!'

    N_chan = np.shape(cim.getdata())[0]

    if close:
        del cim

    return N_chan

# one space should follow each comma (,)
def get_N_pol_from_CIM(cimpath, close=False):
    """Get the number of polarizations from a CASAImage. Note, that the
    polarization type is not returned!

    CASAImage indices: [freq, Stokes, x, y]

    Parameters
    ==========
    cimpath: str
        The input CASAImage path or a ``casacore.images.image.image`` object
    
    close: bool, optional
        If True the in-memory CASAIMage is deleted, and the optional write-lock releases
        Set to true if this is the last operation on the image, but False if other functions
        called that operation on the same image. This avoids multiple read-in of the image.

    Returns
    =======
    N_pol: int
        Number of polarizations in the CASAImage
    """
    cim = ds.cim.create_CIM_object(cimpath)
    assert cim.ndim() == 4, 'The image has more than 4 axes!'

    N_pol = np.shape(cim.getdata())[1]

    if close:
        del cim

    return N_pol

# one space should follow each comma (,)
def check_CIM_equity(cimpath_a, cimpath_b, numprec=1e-8, close=False):
    """Check if two CASAImages are identical or not up to a defined numerical precision
    This function is used to test certain pipeline features.

    Note: NaN-s are treated as equals, and the ``numprec`` parameter only sets the relative difference limit.

    Parameters
    ==========
    cimpath_a: str
        The input CASAImage path of Alice or a ``casacore.images.image.image`` object

    cimpath_b: str
        The input CASAImage path of Bob or a ``casacore.images.image.image`` object

    numprec: float
        The numerical precision limit of the maximum allowed relative
        difference between CASAImages Alice and Bob.
        If set to zero, equity is checked.

    close: bool, optional
        If True the in-memory CASAIMage is deleted, and the optional write-lock releases
        Set to true if this is the last operation on the image, but False if other functions
        called that operation on the same image. This avoids multiple read-in of the image.

    Returns
    =======
    equity: bool
        True or False, base on the equity of Alice and Bob
    """

    cimA = ds.cim.create_CIM_object(cimpath_a)
    cimB = ds.cim.create_CIM_object(cimpath_b)

    assert cimA.ndim() == cimB.ndim(), 'The dimension of the two input CASAImage is not equal!'

    if numprec == 0.:
        equviv = np.array_equiv(cimA.getdata(),cimB.getdata())
    else:
        equviv = np.allclose(cimA.getdata(),cimB.getdata(),atol=0,rtol=numprec,equal_nan=True)

    if close:
        del cimA
        del cimB

    return equviv

def ensure_same_dims(a, b):
    """Checks if the ``a`` and ``b`` image objects have the same number
    of dimensions.
    
    Parameters
    ==========
    a: ``casacore.images.image.image`` object
        In-memory CASAImage
    b: ``casacore.images.image.image`` object
        In-memory CASAImage
    
    Raises
    ======
    AssertionError
        If the number of dimensions is not equal for ``a`` and ``b``.
    
    """
    assert a.ndim() == b.ndim(), 'The dimension of the two input CASAImage is not equal!'
    

# one space should follow each comma (,)
def check_CIM_coordinate_equity(cimpath_a, cimpath_b, close=False):
    """Basic check if the associated coordinate information of two images are somewhat equal.
    This is **not** an equity check for all coordinate values, as the reference pixels can be different,
    even for images (grids) with the same coordinate system. Hence, the rigorous part of the check is
    the increment between channels/pixels. The main idea behind this function is to check if
    images (grids) can be stacked together.

    Note, that the two CASAImages have to be the same dimension!

    The code actually never returns False but fails due to assertion...
    In the future the option to return False instead of assertion can be added to handle
    some weird special cases.

    Parameters
    ==========
    cimpath_a: str
        The input CASAImage path of Alice or a ``casacore.images.image.image`` object

    cimpath_b: str
        The input CASAImage path of Bob or a ``casacore.images.image.image`` object

    close: bool, optional
        If True the in-memory CASAIMages are deleted, and the optional write-lock releases
        Set to true if this is the last operation on the image, but False if other functions
        called that operation on the same image. This avoids multiple read-in of the image.

    Returns
    =======
    equity: bool
        True or False, base on the coordinate equity of Alice and Bob
    """
    cimA = ds.cim.create_CIM_object(cimpath_a)
    cimB = ds.cim.create_CIM_object(cimpath_b)
    
    ensure_same_dims(cimA, cimB)
    # Similarly I would refactor the unit checks.
    assert cimA.unit() == cimB.unit(), 'The pixel units of the two input CASAImage is not equal!'

    coordsA = cimA.coordinates()
    coordsB = cimA.coordinates()

    #Spectral coordinates
    coords_axis = 'spectral'
    
    # Since variables ``coordsA[coords_axis]`` and
    # ``coordsB[coords_axis]`` are used multiple times I would
    # save their value into a separate variable. This also saves
    # some CPU time by executing the "lookup" operation
    # (the [] operator)only once.
    # Similarly other temporary values that are used more than one
    # time, could be saved into a variable. E.g. ``cimA.name()`` and
    # ``cimB.name()``.
    
    axis_a, axis_b = coordsA[coords_axis], coordsB[coords_axis]
    
    assert axis_a.get_frame() == axis_b.get_frame(), \
    'The given images {0:s} and {1:s} have different frames!'.format(cimA.name(),cimB.name())

    if axis_a.get_unit() == axis_b.get_unit():
        assert axis_a.get_increment() == axis_b.get_increment(), \
        'The increment of the two spectral coordinates are different for images {0:s} and {1:s}'.format(
        cimA.name(),cimB.name())
        
        assert axis_a.get_restfrequency() == axis_b.get_restfrequency(), \
        'The rest frame frequency of the two spectral coordinates are different for images {0:s} and {1:s}'.format(
        cimA.name(),cimB.name())

        if axis_a.get_referencepixel() == axis_b.get_referencepixel():
            assert axis_a.get_referencevalue() == axis_b.get_referencevalue(), \
            'The reference values of the spectral corrdinates are different for images {0:s} and {1:s}'.format(
            cimA.name(),cimB.name())
        else:
            warnings.warn('The input images {0:s} and {1:s} have different spectral coordinate reference pixel!'.format(
                    cimA.name(),cimB.name()))
    else:
        warnings.warn('The input images {0:s} and {1:s} have different spectral coordinate units!'.format(
                    cimA.name(),cimB.name()))

    #Polarization coordinates
    coords_axis = 'stokes'

    assert axis_a.get_stokes() == axis_b.get_stokes(), \
    'The polarization frame is different for images {0:s} and {1:s}!'.format(cimA.name(),cimB.name())

    #Direction coordinates if images and linear coordinates if grids
    coords_axis = 'direction'
    try:
        assert axis_a.get_frame() == axis_b.get_frame(), \
        'The given images {0:s} and {1:s} have different frames!'.format(cimA.name(),cimB.name())

        assert axis_a.get_projection() == axis_b.get_projection(), \
        'The given images {0:s} and {1:s} have different projections!'.format(cimA.name(),cimB.name())

    except AssertionError:
        #re-run the assertion to actually fail the code
        assert axis_a.get_frame() == axis_b.get_frame(), \
        'The given images {0:s} and {1:s} have different frames!'.format(cimA.name(),cimB.name())

        assert axis_a.get_projection() == axis_b.get_projection(), \
        'The given images {0:s} and {1:s} have different projections!'.format(cimA.name(),cimB.name())
    
    except:
        #Change to linear coord as the given CASAimage is a grid!
        coords_axis = 'linear'

    if np.all(np.array(axis_a.get_unit()) == np.array(axis_b.get_unit())):
        assert np.all(np.array(axis_a.get_increment()) == np.array(axis_b.get_increment())), \
        'The increment of the (x,y) direction coordinates are different for the input images {0:s} and {1:s}'.format(
        cimA.name(),cimB.name())

        if np.all(np.array(axis_a.get_referencepixel()) == np.array(axis_b.get_referencepixel())):
            assert np.all(np.array(axis_a.get_referencevalue()) == np.array(axis_b.get_referencevalue())), \
            'The reference values of the (x,y) direction corrdinates are different for images {0:s} and {1:s}'.format(
            cimA.name(),cimB.name())
        else:
            warnings.warn('The input images {0:s} and {1:s} have different (x,y) direction coordinate reference pixels!'.format(
                    cimA.name(),cimB.name()))
    else:
        warnings.warn('The input images {0:s} and {1:s} have different (x,y) direction coordinate units!'.format(
                    cimA.name(),cimB.name()))

    if close:
        del cimA
        del cimB

    return True

# one space should follow each comma (,)
def set_CIM_unit(cimpath, unit, overwrite=False):
    """When a CASAImage is created using the ``casaimage.image()`` routine, the pixel unit of the image is empty by default.
    There is no way to set the unit by using the ``casacore.images`` module. However, we can workaround this by opening the
    image as a CASATable. Hooray. When no unit is defined the keyword *units* will be missing, hence we need to add this
    together with the unit value.

    Parameters
    ==========
    cimpath: str
        The input CASAImage path

    unit: str
        The unit of the image pixels e.g. Jy/Beam 

    overwrite: bool, optional
        If True, the existing unit is overwritten with the input ``unit`` parameter

    Returns
    ======= 
    Saves the image with the pixel unit included
    """
    CIMTable = ds.msutil.create_MS_object(cimpath,readonly=False)

    try:
        CIM_unit = CIMTable.getkeyword('units')
        if CIM_unit != unit and overwrite == False:
            warnings.warn('The image {0:s} already has a pixel unit: {1:s} that is different from the given unit: {2:s}!'.format(cimpath,CIM_unit,unit))
        else:
            CIMTable.putkeyword('units', unit)
    except:
        CIMTable.putkeyword('units', unit)

    CIMTable.close()

# one space should follow each comma (,)
def create_CIM_diff_array(cimpath_a, cimpath_b, rel_diff=False, all_dim=False, chan=0, pol=0, close=False):
    """Compute the difference of two CASAImage, and return it as a numpy array.
    Either the entire difference cube, or only the difference of a selected channel 
    and polarization slice is returned.

    The code computes the first minus second image given, and normalizes with the
    second one if the rel_diff parameter is set to True.

    This function makes sense mostly on images not on grids!

    Parameters
    ==========
    cimpath_a: str
        The input CASAImage path of Alice

    cimpath_b: str
        The input CASAImage path of Bob
    
    rel_diff: bool
        If True, the relative difference is returned. The code uses Bob to normalize.

    all_dim: bool
        If True, the difference across all channels and polarizations will be computed.
        Note taht it can be **very slow and memory heavy**!

    chan: int
        Index of the channel in the image cube

    pol: int
        Index of the polarization in the image cube

    close: bool, optional
        If True the in-memory CASAIMage is deleted, and the optional write-lock releases
        Set to true if this is the last operation on the image, but False if other functions
        called that operation on the same image. This avoids multiple read-in of the image.

    Returns
    =======
    diff_array: numpy ndarray
        Either a single channel and polarization slice difference,
        or the difference cube of the two input CASAImages
    """
    cimA = ds.cim.create_CIM_object(cimpath_a)
    cimB = ds.cim.create_CIM_object(cimpath_b)
    
    ensure_same_dims(a, b)

    if all_dim:
        if rel_diff:
            diff_array = np.divide(np.subtract(cimA.getdata(),cimB.getdata()),cimB.getdata())
        else:
            diff_array = np.subtract(cimA.getdata(),cimB.getdata())
    else:
        if rel_diff:
            diff_array = np.divide(np.subtract(cimA.getdata()[chan,pol,...],cimB.getdata()[chan,pol,...]),cimB.getdata()[chan,pol,...])
        else:
            diff_array = np.subtract(cimA.getdata()[chan,pol,...],cimB.getdata()[chan,pol,...])

    if close:
        del cimA
        del cimB            

    return diff_array

# one space should follow each comma (,)
def measure_CIM_RMS(cimpath, all_dim=False, chan=0, pol=0, close=False):
    """Measure the RMS on a CASAImage either for a given channel and polarization,
    or for ALL channels and polarizations. This could be very slow though.

    Parameters
    ==========
    cimgpath: str
        The input CASAImage path

    all_dim: bool
        If True, the RMS will be computed for all channels and polarizations in the image cube
        Note that, this can be **very slow**!

    chan: int
        Index of the channel in the image cube

    pol: int
        Index of the polarization in the image cube

    close: bool, optional
        If True the in-memory CASAIMage is deleted, and the optional write-lock releases
        Set to true if this is the last operation on the image, but False if other functions
        called that operation on the same image. This avoids multiple read-in of the image.

    Returns
    =======
    rms: float or list of floats
        The RMS value for the given channel or a numpy ndarray
        containing the RMS for the corresponding channel and polarization
    
    """
    cim = ds.cim.create_CIM_object(cimpath)

    if all_dim:
        rms_matrix = np.zeros((cim.shape()[0],cim.shape()[1]))

        # I will think about how this operation could be vectorised
        # so ther will be no need for Python loops.
        for chan_i in range(0,cim.shape()[0]):
            for pol_j in range(0,cim.shape()[1]):
                rms_matrix[i,j] = np.sqrt(np.mean(np.square(cim.getdata()[chan_i,pol_j,...])))

        if close:
            del cim
        return rms_matrix

    else:
        rms = np.sqrt(np.mean(np.square(cim.getdata()[chan,pol,...])))
        if close:
            del cim
        return rms

# one space should follow each comma (,)
def CIM_stacking_base(cimpath_list, cim_output_path, cim_outputh_name, normalise=False,overwrite=False):
    """This function is one of the core functions of the image stacking stacking deep spectral line pipelines.

    This function takes a list of CASAImages and creates the stacked CASAIMage.
    The resultant image can be a simple sum or an average.

    The given images have to have the same:
        - shape
        - coordinates
        - pixel value unit (e.g. Jy/beam)

    NOTE, that there are better tools in YadaSoft and casacore to create stacked images,
    but no option to stack and modify grids.

    Parameters
    ==========
    cimpath_list: list
        A list of the full paths of the images to be stacked
    
    cim_output_path: str
        Full path to the folder in which the stacked image will be saved

    cim_outputh_name: str
        Name of the stacked image

    normalise: bool
        If True, the images will be averaged instead of just summing them
    
    overwrite: bool
        If True, the stacked image will be created regardless if another image exist
        in the same name. Note, that in this case the existing grid will be deleted!

    Returns
    ========
    Stacked image: CASAImage
        Create the stacked image at ``cim_output_path/cim_outputh_name``

    """
    assert len(cimpath_list) >= 2, 'Less than two image given for stacking!'

    output_cim = '{0:s}/{1:s}'.format(cim_output_path,cim_outputh_name)

    if os.path.isdir(output_cim): assert overwrite, 'Stacked image already exist, and the overwrite parameters is set to False!'

    base_cim = ds.cim.create_CIM_object(cimpath_list[0])

    #Coordinate system is initialized by the first CASAImages coordinate system
    coordsys = base_cim.coordinates()

    check_attrgroup_empty = lambda x: None if x.attrgroupnames() == [] else warnings.warn('Input image {0:s} has a non-empty attribute list!'.format(x.name()))
    check_history_empty = lambda x: None if x.history() == [] else warnings.warn('Input image {0:s} has a non-empty history field!'.format(x.name()))

    check_attrgroup_empty(base_cim)
    check_history_empty(base_cim)

    #If shape is given, the data type is automatically set to float!
    stacked_cim = casaimage.image(output_cim,
                    coordsys=coordsys,
                    values=base_cim.getdata(),
                    overwrite=overwrite)
    
    #Keep the data in memory
    stacked_cim_data = base_cim.getdata()

    #Close the image so the unit can be set
    del stacked_cim

    #Set the unit of the resultant image based on the first image
    ds.cim.set_CIM_unit(output_cim, base_cim.unit())

    #Read back the stacked image
    stacked_cim = ds.cim.create_CIM_object(output_cim)

    for i in range(1,len(cimpath_list)):
        cim = ds.cim.create_CIM_object(cimpath_list[i])

        assert base_cim.datatype() == cim.datatype(), 'The data type of the two input images ({0:s} and {1:s}) are not equal!'.format(base_cim.name(),cim.name())
        assert base_cim.ndim() == cim.ndim(), 'The dimension of the two input images ({0:s} and {1:s}) are not equal!'.format(base_cim.name(),cim.name())
        assert ds.cim.check_CIM_coordinate_equity(cim,stacked_cim), \
        'The created stacked image and the image {0:s} have different coordinate systems!'.format(cim.name())

        check_attrgroup_empty(cim)
        check_history_empty(cim)

        stacked_cim_data = np.add(stacked_cim_data, cim.getdata())

    if normalise:
        stacked_cim_data = np.divide(stacked_cim_data,len(cimpath_list))

    stacked_cim.putdata(stacked_cim_data)

    #Deleting the CIM variable closes the image, which release the lock
    del stacked_cim
    del output_cim
    del base_cim


if __name__ == "__main__":
    CIM_stacking_base(['/home/krozgonyi/Desktop/list_imaging_test/dumpgrid_first_night/image.restored.test',
                    '/home/krozgonyi/Desktop/list_imaging_test/dumpgrid_second_night/image.restored.test'],
                    '/home/krozgonyi/Desktop','a.image', normalise=True,overwrite=True)
