#
#
# Copyright 2013-2016 Universidad Complutense de Madrid
#
# This file is part of PyEmir
#
# PyEmir is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyEmir is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyEmir.  If not, see <http://www.gnu.org/licenses/>.
#

'''Recipe to detect slits in the AIV mask'''

from __future__ import division
#
import logging
# import math
#
import numpy
# import scipy.interpolate as itpl
# import scipy.optimize as opz
# from astropy.modeling import models, fitting
from astropy.io import fits
# import photutils
#
# from numina.array.recenter import img_box, centering_centroid
#
from numina import __version__
from numina.flow.processing import BiasCorrector, DarkCorrector
from numina.flow.processing import SkyCorrector
from numina.flow.processing import Corrector
from numina.flow import SerialFlow
from numina.flow.node import IdNode
from numina.array import combine
#
from emirdrp.core import EMIR_BIAS_MODES
from emirdrp.core import gather_info


_logger = logging.getLogger('numina.recipes.emir')


class BadPixelCorrectorEmir(Corrector):
    '''A Node that corrects a frame from bad pixels.'''

    def __init__(self, badpixelmask, mark=True, tagger=None,
                 datamodel=None, dtype='float32'):

        super(BadPixelCorrectorEmir, self).__init__(datamodel,
                                                    tagger=tagger,
                                                    dtype=dtype)

        self.bpm = badpixelmask
        self.good_vals = (self.bpm == 0)
        self.bad_vals = ~self.good_vals
        self.median_box = 5

    def _run(self, img):
        import scipy.ndimage as snd
        # global median
        imgid = self.get_imgid(img)
        _logger.debug('correcting bad pixel mask in %s', imgid)
        base = img[0].data
        interp = base.copy()
        mask1 = ~numpy.isfinite(base)
        # Fill BPM with median values
        median = numpy.median(base[self.good_vals])
        interp[self.bad_vals] = median
        interp = snd.median_filter(interp, size=self.median_box)
        #
        img[0].data[self.bad_vals] = interp[self.bad_vals]

        mask1 = ~numpy.isfinite(base)
        if numpy.any(mask1):
            _logger.warning('image has %d NaN', mask1.sum())

        mask2 = ~numpy.isfinite(img[0].data)
        if numpy.any(mask2):
            _logger.warning('image has %d NaN', mask2.sum())

        return img


class FlatFieldCorrector(Corrector):
    '''A Node that corrects a frame from flat-field.'''

    def __init__(self, flatdata, datamodel=None, mark=True,
                 tagger=None, dtype='float32'):

        self.update_variance = False

        super(FlatFieldCorrector, self).__init__(
            datamodel=datamodel,
            tagger=tagger,
            dtype=dtype)

        self.flatdata = flatdata
        self.flatdata[flatdata <= 0] = 1.0 # To avoid NaN
        self.flat_stats = flatdata.mean()

    def _run(self, img):
        import numina.array as array
        imgid = self.get_imgid(img)

        _logger.debug('correcting flat in %s', imgid)
        _logger.debug('flat mean is %f', self.flat_stats)

        data = self.datamodel.get_data(img)
        # data = array.correct_flatfield(data, self.flatdata, dtype=self.dtype)
        # Check if flatdata as 0
        mask1 = self.flatdata < 0
        if numpy.any(mask1):
            _logger.warning('flat has %d zeros', mask1.sum())
        mask2 = ~numpy.isfinite(data)
        if numpy.any(mask2):
            _logger.warning('image has %d NaN', mask2.sum())

        result = data / self.flatdata
        result = result.astype(self.dtype)

        # FIXME
        img[0].data = result
        return img


class Checker(Corrector):
    '''A Node that checks.'''
    def __init__(self):
        super(Checker, self).__init__(None)

    def _run(self, img):
        base = img[0].data
        _logger.debug('running checker after flat')
        # Check NaN and Ceros
        mask1 = ~numpy.isfinite(base)
        if numpy.any(mask1):
            _logger.warning('image has %d NaN', mask1.sum())

        return img


def init_filters_generic(rinput, getters):
    # with BPM, bias, dark, flat and sky
    meta = gather_info(rinput)

    correctors = [getter(rinput, meta) for getter in getters]

    flow = SerialFlow(correctors)

    return flow


def init_filters_pbdfs(rinput):
    # with BPM, bias, dark, flat and sky

    # Methods required:
    getters = [get_corrector_p,
               get_corrector_b,
               get_corrector_d,
               get_corrector_f,
               get_checker,
               get_corrector_s
    ]

    return init_filters_generic(rinput, getters)

def init_filters_pbdf(rinput):
    # with BPM, bias, dark, flat

    # Methods required:
    getters = [get_corrector_p,
               get_corrector_b,
               get_corrector_d,
               get_corrector_f,
    ]

    return init_filters_generic(rinput, getters)


def init_filters_pbd(rinput):
    # with BPM, bias, dark

    # Methods required:
    getters = [get_corrector_p,
               get_corrector_b,
               get_corrector_d,
    ]

    return init_filters_generic(rinput, getters)


def init_filters_pb(rinput):
    # with BPM, bias

    # Methods required:
    getters = [get_corrector_p,
               get_corrector_b,
    ]

    return init_filters_generic(rinput, getters)


def init_filters_p(rinput):
    # with BPM

    # Methods required:
    getters = [get_corrector_p]

    return init_filters_generic(rinput, getters)


# Alias for backwards compatibility
init_filters_b = init_filters_pb
init_filters_bd = init_filters_pbd
init_filters_bdf = init_filters_pbdf
init_filters_bdfs = init_filters_pbdfs


def get_corrector_p(rinput, meta):

    bpm_info = meta.get('master_bpm')
    if bpm_info is not None:
        with rinput.master_bpm.open() as hdul:
            _logger.info('loading BPM')
            _logger.debug('BPM image: %s', bpm_info)
            mbpm = hdul[0].data
            bpm_corrector = BadPixelCorrectorEmir(mbpm)
    else:
        _logger.info('BPM not provided, ignored')
        bpm_corrector = IdNode()

    return bpm_corrector


def get_corrector_b(rinput, meta):
    iinfo = meta['obresult']
    _logger.debug('images info: %s', iinfo)
    if iinfo:
        mode = iinfo[0]['readmode']
        if mode.lower() in EMIR_BIAS_MODES:
            use_bias = True
            _logger.info('readmode is %s, bias required', mode)
        else:
            use_bias = False
            _logger.info('readmode is %s, bias not required', mode)
    else:
        raise ValueError('cannot gather images info')

    # Loading calibrations
    if use_bias:
        bias_info = meta['master_bias']
        with rinput.master_bias.open() as hdul:
            _logger.info('loading bias')
            _logger.debug('bias info: %s', bias_info)
            mbias = hdul[0].data
            bias_corrector = BiasCorrector(mbias)
    else:
        _logger.info('ignoring bias')
        bias_corrector = IdNode()

    return bias_corrector


def get_corrector_s(rinput, meta):
    sky_info = meta['master_sky']


    with rinput.master_sky.open() as msky_hdul:
        _logger.info('loading sky')
        _logger.debug('sky info: %s', sky_info)
        msky = msky_hdul[0].data
        sky_corrector = SkyCorrector(msky)

    return sky_corrector


def get_corrector_f(rinput, meta):
    flat_info = meta['master_flat']

    with rinput.master_flat.open() as mflat_hdul:
        _logger.info('loading intensity flat')
        _logger.debug('flat info: %s', flat_info)
        mflat = mflat_hdul[0].data
        # Check NaN and Ceros
        mask1 = mflat < 0
        mask2 = ~numpy.isfinite(mflat)
        if numpy.any(mask1):
            _logger.warning('flat has %d values below 0', mask1.sum())
        if numpy.any(mask2):
            _logger.warning('flat has %d NaN', mask2.sum())
        flat_corrector = FlatFieldCorrector(mflat)

    return flat_corrector


def get_corrector_d(rinput, meta):
    key = 'master_dark'
    CorrectorClass = DarkCorrector

    info = meta[key]
    req = getattr(rinput, key)
    with req.open() as hdul:
        _logger.info('loading %s', key)
        _logger.debug('%s info: %s', key, info)
        datac = hdul[0].data
        corrector = CorrectorClass(datac)

    return corrector


def get_checker(rinput, meta):

    return Checker()


def basic_processing_with_combination(rinput, flow,
                                      method=combine.mean,
                                      errors=True):
    odata = []
    cdata = []
    try:
        _logger.info('processing input images')
        for frame in rinput.obresult.images:
            hdulist = frame.open()
            fname = hdulist.filename()
            if fname:
                _logger.info('input is %s', fname)
            else:
                _logger.info('input is %s', hdulist)

            final = flow(hdulist)
            _logger.debug('output is input: %s', final is hdulist)

            cdata.append(final)

            # Files to be closed at the end
            odata.append(hdulist)
            if final is not hdulist:
                odata.append(final)

        _logger.info("stacking %d images using 'mean'", len(cdata))
        data = method([d[0].data for d in cdata], dtype='float32')
        hdu = fits.PrimaryHDU(data[0], header=cdata[0][0].header.copy())
        hdu.header['NUMXVER'] = (__version__, 'Numina package version')
        if errors:
            varhdu = fits.ImageHDU(data[1], name='VARIANCE')
            num = fits.ImageHDU(data[2], name='MAP')
            result = fits.HDUList([hdu, varhdu, num])
        else:
            result = fits.HDUList([hdu])
    finally:
        _logger.debug('closing images')
        for hdulist in odata:
            hdulist.close()

    _logger.debug('update result header')

    return result


def basic_processing_with_update(rinput, flow):

    # FIXME: this only works with local images
    # We don't know how to store temporary GCS frames
    _logger.info('processing input images')
    for frame in rinput.obresult.images:
        with fits.open(frame.label, mode='update') as hdul:
            flow(hdul)
