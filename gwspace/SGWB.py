#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ==================================
# File Name: SGWB.py
# Author: Zhiyuan Li
# Mail:
# ==================================

import numpy as np
import healpy as hp
from healpy import Alm
from sympy.physics.quantum.cg import CG

from gwspace import response
from gwspace.Orbit import detectors
from gwspace.wrap import frequency_noise_from_psd
from gwspace.constants import H0_SI


class SGWB(object):
    """ Generate the anisotropy SGWB signal in frequency domain

    :param fmax,fmin(Hz): the maximum and minimum frequency we generate
    :param fn: the frequency segment number
    :param tsegmid(s): the time segment length,for TQ we usually use 5000s or 3600s，The ORF error is less than 3%
    :param Ttot(s): the total observe time, unit : second
    :param omega0: the intensity of the signal at reference frequency
    :param alpha: the power-law index
    :param nside_in: determine the pixel number, we usually use 8,12,16...
    :param blm_vals: A series of spherical coefficients
    :param blmax: the order of blm_vals
    :param fref(Hz): the reference frequency
    :param H0: Hubble constant
    :param det: the detector type
    """

    def __init__(self, fmax, fmin, fn, tsegmid, Ttot, omega0, alpha, nside_in, blm_vals, blmax,
                 fref=0.01, H0=H0_SI, det="TQ"):
        self.fmax = fmax
        self.fmin = fmin
        self.fn = fn
        self.tsegmid = tsegmid
        self.Ttot = Ttot
        self.fref = fref
        self.omega0 = omega0
        self.alpha = alpha
        self.nside_in = nside_in
        self.blm_vals = blm_vals
        self.blmax = blmax
        self.num_blms = Alm.getsize(self.blmax)
        self.blms = np.zeros(self.num_blms, dtype='complex')
        self.H0 = H0
        # self.detectors = detector
        for ii in range(self.num_blms):
            self.blms[ii] = complex(blm_vals[ii])
        self.almax = 2*self.blmax
        self.alm_size = (self.almax+1)**2
        self.blm_size = Alm.getsize(self.blmax)
        self.bl_idx = np.zeros(2*self.blm_size-self.blmax-1, dtype='int')
        self.bm_idx = np.zeros(2*self.blm_size-self.blmax-1, dtype='int')
        for ii in range(self.bl_idx.size):
            # lval, mval = Alm.getlm(blmax, jj)
            self.bl_idx[ii], self.bm_idx[ii] = self.idx_2_alm(blmax, ii)
        alms_inj = self.blm_2_alm(self.blms)
        alms_inj2 = alms_inj/(alms_inj[0]*np.sqrt(4*np.pi))
        # extract only the non-negative components
        alms_non_neg = alms_inj2[0:hp.Alm.getsize(self.almax)]

        self.skymap_inj = hp.alm2map(alms_non_neg, self.nside_in)
        self.frange = np.linspace(self.fmin, self.fmax, self.fn)
        tf = np.arange(0, Ttot, tsegmid)
        Omegaf = self.omega0*(self.frange/self.fref)**self.alpha
        Sgw = Omegaf*(3/(4*self.frange**3))*(self.H0/np.pi)**2
        Sgw_Gu = frequency_noise_from_psd(Sgw, 1/Ttot, seed=123)
        self.signal_in_Gu = np.einsum('i,j->ij', (2/Ttot)*Sgw_Gu*Sgw_Gu.conj(), self.skymap_inj)  # Gaussian signal
        npix = hp.nside2npix(self.nside_in)
        # Array of pixel indices
        pix_idx = np.arange(npix)
        # Angular coordinates of pixel indices
        self.thetas, self.phis = hp.pix2ang(self.nside_in, pix_idx)
        self.e_plus = np.einsum("ik,jk->ijk", self.vec_v, self.vec_v)-np.einsum("ik,jk->ijk", self.vec_u, self.vec_u)
        self.e_cross = np.einsum("ik,jk->ijk", self.vec_u, self.vec_v)+np.einsum("ik,jk->ijk", self.vec_v, self.vec_u)
        det = detectors[det](tf)
        # det = TianQinOrbit(tf)
        self.TQresponse_plus = np.zeros((3, self.frange.size, tf.size, npix), dtype="complex")
        self.TQresponse_cross = np.zeros((3, self.frange.size, tf.size, npix), dtype="complex")
        for i in range(npix):
            for j in range(self.frange.size):
                TQreplus = response.trans_y_slr_fd(self.vec_k[:, i], self.e_plus[:, :, i], det, self.frange[j])[0]
                TQxyz_plus = response.get_XYZ_fd(TQreplus, self.frange[j], det.L_T)
                self.TQresponse_plus[:, j, :, i] = TQxyz_plus
                TQrecross = response.trans_y_slr_fd(self.vec_k[:, i], self.e_cross[:, :, i], det, self.frange[j])[0]
                TQxyz_cross = response.get_XYZ_fd(TQrecross, self.frange[j], det.L_T)
                self.TQresponse_cross[:, j, :, i] = TQxyz_cross
        # TQ_ORF is 3*3*frequency*t*pixel
        self.TQ_ORF = (1/(8*np.pi))*(np.einsum("mjkl,njkl->mnjkl", np.conj(self.TQresponse_plus), self.TQresponse_plus)
                                     + np.einsum("mjkl,njkl->mnjkl", np.conj(self.TQresponse_cross), self.TQresponse_cross))/(
                                  2*np.pi*self.frange[None, None, :, None, None]*det.L_T)**2
        response_signal = self.signal_in_Gu[None, None, :, None, :]*self.TQ_ORF
        self.signal_SGWB = (4*np.pi)*np.sum(response_signal, axis=4)/npix

    def calc_beta(self):
        beta_vals = np.zeros((self.alm_size, 2*self.blm_size-self.blmax-1, 2*self.blm_size-self.blmax-1))

        for ii in range(beta_vals.shape[0]):
            for jj in range(beta_vals.shape[1]):
                for kk in range(beta_vals.shape[2]):
                    l1, m1 = self.idx_2_alm(self.blmax, jj)
                    l2, m2 = self.idx_2_alm(self.blmax, kk)
                    L, M = self.idx_2_alm(self.almax, ii)

                    # Clebsch-Gordan coefficient
                    cg0 = (CG(l1, 0, l2, 0, L, 0).doit()).evalf()
                    cg1 = (CG(l1, m1, l2, m2, L, M).doit()).evalf()

                    beta_vals[ii, jj, kk] = np.sqrt((2*l1+1)*(2*l2+1)/((4*np.pi)*(2*L+1))) * cg0 * cg1

        return beta_vals

    def calc_blm_full(self, blms_in):
        # Array of blm values for both +ve and -ve indices
        blms_full = np.zeros(2*self.blm_size-self.blmax-1, dtype='complex')

        for jj in range(blms_full.size):

            lval, mval = self.bl_idx[jj], self.bm_idx[jj]

            if mval >= 0:
                blms_full[jj] = blms_in[Alm.getidx(self.blmax, lval, mval)]

            elif mval < 0:
                mval = -mval
                blms_full[jj] = (-1)**mval * np.conj(blms_in[Alm.getidx(self.blmax, lval, mval)])

        return blms_full

    def blm_2_alm(self, blms_in):

        beta_vals = self.calc_beta()
        if blms_in.size != self.blm_size:
            raise ValueError('The size of the input blm array does not match the size defined by lmax ')

        # convert blm array into a full blm array with -m values too
        blm_full = self.calc_blm_full(blms_in)

        alm_vals = np.einsum('ijk,j,k', beta_vals, blm_full, blm_full)

        return alm_vals

    @staticmethod
    def idx_2_alm(lmax, ii):
        """ index --> (l, m) function which works for negative indices too """
        alm_size = Alm.getsize(lmax)
        if ii >= (2*alm_size-lmax-1):
            raise ValueError('Index larger than acceptable')
        elif ii < alm_size:
            l, m = Alm.getlm(lmax, ii)
        else:
            l, m = Alm.getlm(lmax, ii-alm_size+lmax+1)

            if m == 0:
                raise ValueError('Something wrong with ind -> (l, m) conversion')
            else:
                m = -m
        return l, m

    @property
    def vec_u(self):
        return np.array([-np.sin(self.phis), np.cos(self.phis), np.zeros(len(self.phis))])

    @property
    def vec_v(self):
        return np.array([np.cos(self.phis)*np.cos(self.thetas),
                         np.cos(self.thetas)*np.sin(self.phis),
                         -np.sin(self.thetas)])

    @property
    def vec_k(self):
        return np.array([-np.sin(self.thetas)*np.cos(self.phis),
                         -np.sin(self.thetas)*np.sin(self.phis),
                         -np.cos(self.thetas)])  # Vector of sources
