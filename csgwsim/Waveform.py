#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ==================================
# File Name: Waveform.py
# Author: ekli
# Mail: lekf123@163.com
# Created Time: 2023-08-01 12:32:36
# ==================================

import numpy as np
from numpy import sin, cos, sqrt

from .Constants import MSUN_SI, MSUN_unit, MPC_SI, YRSID_SI, PI, C_SI, G_SI
from .FastEMRI import EMRIWaveform


# Note1: one can use __slots__=('mass1', 'mass2', 'etc') to fix the attributes
#        then the class will not have __dict__ anymore, and attributes in __slots__ are read-only.
# Note2: One can use @DynamicAttrs to avoid warnings of 'no attribute'.
class BasicWaveform(object):
    """
    Class for waveform
    -------------------------------
    Parameters:
    - pars: dict of parameters for different sources
    such as:
        - type: GCB; BHB; EMRI; SGWB for different sources
        - lambda: longitude of the source in ecliptic coordinates
        - beta: latitude of the source in ecliptic coordinates
        - psi: polarization angle
        - iota: inclination angle
        - Mc: chirp mass
        - DL: luminosity distance
        - etc
    """
    __slots__ = ('mass1', 'mass2', 'T_obs', 'DL', 'Lambda', 'Beta',
                 'phi_c', 'tc', 'iota', 'var_phi', 'psi', 'add_para')

    def __init__(self, mass1, mass2, T_obs, DL=1., Lambda=None, Beta=None,
                 phi_c=0., tc=0., iota=0., var_phi=0., psi=0, **kwargs):
        self.DL = DL
        self.mass1 = mass1
        self.mass2 = mass2
        self.Lambda = Lambda
        self.Beta = Beta
        self.phi_c = phi_c
        self.T_obs = T_obs
        self.tc = tc
        self.iota = iota
        self.var_phi = var_phi
        self.psi = psi
        self.add_para = kwargs

    # @property
    # def redshift(self):
    #     return float(dl_to_z(self.DL))

    # @property
    # def z(self):
    #     return self.redshift

    @property
    def Mt(self):
        return self.mass1 + self.mass2  # Total mass (solar mass)

    @property
    def eta(self):
        return self.mass1 * self.mass2 / self.Mt**2  # Symmetric mass ratio

    @property
    def Mc(self):
        return self.eta**(3/5) * self.Mt  # Chirp mass (solar mass)

    @property
    def vec_u(self):
        return np.array([sin(self.Lambda), -cos(self.Lambda), 0])

    @property
    def vec_v(self):
        return np.array([-sin(self.Beta)*cos(self.Lambda),
                         -sin(self.Beta)*sin(self.Lambda),
                         cos(self.Beta)])

    @property
    def vec_k(self):
        return np.array([-cos(self.Beta)*cos(self.Lambda),
                         -cos(self.Beta)*sin(self.Lambda),
                         -sin(self.Beta)])  # Vector of sources

    def _p0(self):
        """See "LDC-manual-002.pdf" (Eq. 12, 13) & Marsat et al. (Eq. 14)"""
        sib, csb = sin(self.Beta), cos(self.Beta)
        sil, csl = sin(self.Lambda), cos(self.Lambda)
        sil2, csl2 = sin(2*self.Lambda), cos(2*self.Lambda)

        p0_plus = np.array([-sib**2 * csl**2 + sil**2, (sib**2+1)*(-sil*csl),  sib*csb*csl,
                            (sib**2+1)*(-sil*csl),     -sib**2*sil**2+csl**2,  sib*csb*sil,
                            sib*csb*csl,                sib*csb*sil,          -csb**2]).reshape(3, 3)
        p0_cross = np.array([-sib*sil2, sib*csl2,  csb*sil,
                             sib*csl2,  sib*sil2, -csb*csl,
                             csb*sil,  -csb*csl,   0]).reshape(3, 3)
        return p0_plus, p0_cross  # uu-vv, uv+vu

    def polarization(self):
        """See "LDC-manual-002.pdf" (Eq. 19)"""
        p0_plus, p0_cross = self._p0()
        p_plus = p0_plus*cos(2*self.psi) + p0_cross*sin(2*self.psi)
        p_cross = - p0_plus*sin(2*self.psi) + p0_cross*cos(2*self.psi)
        return p_plus, p_cross


class BurstWaveform(object):
    """
    A sin-Gaussian waveforms for poorly modelled burst source
    --------------------------------------------------------
    """

    def __init__(self, amp, tau, fc, tc=0):
        self.amp = amp
        self.tau = tau
        self.fc = fc
        self.tc = tc

    def __call__(self, tf):
        t = tf-self.tc
        h = (2/np.pi)**0.25 * self.tau**(-0.5) * self.amp
        h *= np.exp(- (t/self.tau)**2)*np.exp(2j*np.pi*self.fc*t)
        return h.real, h.imag


class BHBWaveform(BasicWaveform):
    """
    This is Waveform for BHB
    ------------------------
    Parameters:
    - m1, m2: mass of black holes
    - chi1, chi2: spin of the two black holes
    - DL: in MPC
    """
    __slots__ = ('chi1', 'chi2', 'h22')
    # _true_para_key = ('DL', 'Mc', 'eta', 'chi1', 'chi2', 'phi_c', 'iota', 'tc', 'var_phi', 'psi', 'Lambda', 'Beta')
    # fisher_key = ('Mc', 'eta', 'chi1', 'chi2', 'DL', 'phi_c', 'iota', 'tc', 'Lambda', 'Beta', 'psi')

    def __init__(self, mass1, mass2, T_obs, DL=1., Lambda=None, Beta=None,
                 phi_c=0., tc=0., iota=0., var_phi=0., psi=0., chi1=0., chi2=0., **kwargs):

        BasicWaveform.__init__(self, mass1, mass2, T_obs, DL, Lambda, Beta,
                               phi_c, tc, iota, var_phi, psi, **kwargs)
        self.chi1 = chi1
        self.chi2 = chi2
        # self.MfRef_in = MfRef_in
        # self.fRef = fRef  # 0.

        # if not det_frame_para:
        #     self.raw_source_masses = {'mass1': self.mass1, 'mass2': self.mass2,
        #                               'M': self.M, 'Mc': self.Mc}
        #     self.mass1 *= 1+self.z
        #     self.mass2 *= 1+self.z

    # def __eq__(self, other):
    #     return all([getattr(self, key) == getattr(other, key) for key in self._true_para_key])

    @property
    def f_min(self):
        return 5**(3/8)/(8*np.pi) * (MSUN_unit*self.Mc)**(-5/8) * self.T_obs**(-3/8)

    def _y22(self):
        """See "LDC-manual-002.pdf" (Eq. 31)"""
        y22_o = sqrt(5/4/PI) * cos(self.iota/2)**4 * np.exp(2j*self.var_phi)
        y2_2_conj = sqrt(5/4/PI) * sin(self.iota/2)**4 * np.exp(2j*self.var_phi)
        return y22_o, y2_2_conj

    # p_lm(self, l=2, m=2):
    #     y_lm_o = spin_weighted_spherical_harmonic(-2, l, m, self.iota, self.var_phi)
    #     y_l_m_conj = spin_weighted_spherical_harmonic(-2, l, -m, self.iota, self.var_phi).conjugate()
    @property
    def p22(self):
        """See Marsat et al. (Eq. 16) https://journals.aps.org/prd/abstract/10.1103/PhysRevD.103.083011"""
        y22_o, y2_2_conj = self._y22()
        p0_plus, p0_cross = self._p0()
        
        return (1/2 * y22_o * np.exp(-2j*self.psi) * (p0_plus + 1j*p0_cross) +
                1/2 * y2_2_conj * np.exp(2j*self.psi) * (p0_plus - 1j*p0_cross))

    def wave_para_phenomd(self, f_ref=0.):
        """Convert parameters to a list, specially for getting waveform from `pyIMRPhenomD`."""
        phi_ref = self.phi_c
        m1_si = self.mass1 * MSUN_SI
        m2_si = self.mass2 * MSUN_SI
        chi1, chi2 = self.chi1, self.chi2
        dl_si = self.DL * MPC_SI
        return phi_ref, f_ref, m1_si, m2_si, chi1, chi2, dl_si

    def h22_FD(self, freq, fRef=0., t0=0.):
        NF = freq.shape[0]

        amp_imr = np.zeros(NF)
        phase_imr = np.zeros(NF)
        if PyIMRC.findT:
            time_imr = np.zeros(NF)
            timep_imr = np.zeros(NF)
        else:
            time_imr = np.zeros(0)
            timep_imr = np.zeros(0)

        # Create structure for Amp/phase/time FD waveform
        self.h22 = pyIMRD.AmpPhaseFDWaveform(NF, freq, amp_imr, phase_imr, time_imr, timep_imr, fRef, t0)

        # Generate h22 FD amplitude and phase on a given set of frequencies
        self.h22 = pyIMRD.IMRPhenomDGenerateh22FDAmpPhase(self.h22, freq, *self.wave_para_phenomd())

        return self.h22

    def get_amp_phase(self, freq, mode=None):
        """
        Generate the amp and phase in frequency domain
        ----------------------------------------------
        Parameters:
        -----------
        - freq: frequency list
        - mode: mode of GW
        # FIXME: Default argument value is mutable if mode=[(2, 2)], use tuple instead, btw it is unused

        Return:
        -------
        - amp:
        - phase:
        - tf: time of freq
        - tfp: dt/df
        """
        h22 = self.h22_FD(freq, self.fRef, self.tc)

        amp = {(2, 2): h22.amp}
        phase = {(2, 2): h22.phase}
        tf = {(2, 2): h22.time}
        tfp = {(2, 2): h22.timep}

        return amp, phase, tf, tfp


class BHBWaveformEcc(BasicWaveform):
    """Waveform Parameters including eccentricity, using EccentricFD Waveform."""
    __slots__ = 'eccentricity'

    def __init__(self, mass1, mass2, T_obs, DL=1., Lambda=None, Beta=None,
                 phi_c=0., tc=0., iota=0., var_phi=0., psi=0., eccentricity=0., **kwargs):
        BasicWaveform.__init__(self, mass1, mass2, T_obs, DL, Lambda, Beta,
                               phi_c, tc, iota, var_phi, psi, **kwargs)
        self.eccentricity = eccentricity

    @property
    def f_min(self):
        return 5**(3/8)/(8*np.pi) * (MSUN_unit*self.Mc)**(-5/8) * self.T_obs**(-3/8)

    def wave_para(self):
        args = {'mass1': self.mass1*MSUN_SI,
                'mass2': self.mass2*MSUN_SI,
                'distance': self.DL*MPC_SI,
                'coa_phase': self.phi_c,
                'inclination': self.iota,
                'long_asc_nodes': self.var_phi,
                'eccentricity': self.eccentricity}
        return args

    def gen_ori_waveform(self, delta_f=None, f_min=None, f_max=1.):
        """Generate f-domain TDI waveform(EccentricFD)"""
        from .eccentric_fd import gen_ecc_fd_and_tf

        if not f_min:
            f_min = self.f_min
        if delta_f is None:
            delta_f = 1/self.T_obs

        return gen_ecc_fd_and_tf(self.tc, **self.wave_para(), delta_f=delta_f,
                                 f_lower=f_min, f_final=f_max, obs_time=0)

    def fd_tdi_response(self, channel='A', det='TQ', delta_f=None, f_min=None, f_max=1.):
        """Generate F-Domain TDI response for eccentric waveform (EccentricFD).
         Although the eccentric waveform also have (l, m)=(2,2), it has eccentric harmonics,
         which should also calculate separately like what we should do for spherical harmonics."""
        from .Orbit import detectors
        from .response import get_fd_response

        if det not in detectors.keys():
            raise ValueError(f"[SpaceResponse] Unknown detector {det}. "
                             f"Supported detectors: {'|'.join(detectors.keys())}")
        det_class = detectors[det]
        wf, freq = self.gen_ori_waveform(delta_f, f_min, f_max)

        gw_tdi = np.zeros(shape=(len(freq), ), dtype=np.complex128)
        t_delay = np.exp(2j*PI*freq*self.tc)
        p_p, p_c = self.polarization()
        for i in range(10):
            h_p, h_c, tf_vec = wf[i]
            index = (h_p != 0).argmax()

            det = det_class(tf_vec[index:], kappa0=0.)
            gw_tdi_p, gw_tdi_c = get_fd_response(self.vec_k, (p_p, p_c), det, freq[index:], channel)
            gw_tdi[index:] += gw_tdi_p*h_p[index:] + gw_tdi_c*h_c[index:]

        return gw_tdi*t_delay


class GCBWaveform(BasicWaveform):
    """
    This is Waveform for GCB.
    ------------------------
    Parameters:
    - Mc: chirp mass
    - DL: luminosity distance
    - phi0: initial phase at t = 0
    - f0: frequency of the source
    - fdot: derivative of frequency: df/dt
        - default: None, calculated physically
    - fddot: double derivative of frequency: d^2f/dt^2
        - default: None, calculated physically
    --------------------------
    How to call it:
    ```python
    ```
    tf = np.arange(0,Tobs, delta_T)
    GCB = GCBWaveform(Mc=0.5, DL=0.3, phi0=0, f0=0.001)
    hpS, hcS = GCB(tf)
    """

    def __init__(self, mass1, mass2, T_obs, DL, phi0, f0, fdot=None, fddot=None, **kwargs):
        BasicWaveform.__init__(self, mass1, mass2, T_obs, DL, **kwargs)
        # m1, m2 = to_m1m2(Mc, eta)
        Mc = self.Mc
        self.phi0 = phi0
        self.f0 = f0
        # self.fdot = fdot
        if fdot is None:
            self.fdot = (96/5*PI**(8/3) *
                         (G_SI*Mc*MSUN_SI/C_SI**3)**(5/3)
                         * f0**(11/3))
        else:
            self.fdot = fdot
        if fddot is None:
            self.fddot = 11/3*self.fdot**2/f0
        else:
            self.fddot = fddot
        self.amp = 2*(G_SI*Mc*MSUN_SI)**(5/3)
        self.amp = self.amp/C_SI**4/(DL*MPC_SI)
        self.amp = self.amp*(PI*f0)**(2/3)

    def get_hphc(self, t):  # FIXME // name of the fucntion
        phase = 2*PI*(self.f0+0.5*self.fdot*t +
                      1/6*self.fddot*t*t)*t+self.phi0
        hp = self.amp*cos(phase)
        hc = self.amp*sin(phase)

        # TODO: What do we really want from __call__? Original wf or SSB wf?
        #  Could we not use __call__ but add two normal methods in class?
        cs2p = cos(2*self.psi)
        sn2p = sin(2*self.psi)
        csi = cos(self.iota)

        hp_SSB = -(1+csi*csi)*hp*cs2p+2*csi*hc*sn2p
        hc_SSB = -(1+csi*csi)*hp*sn2p-2*csi*hc*cs2p

        return hp_SSB, hc_SSB


class FastGB(GCBWaveform):
    """
    Calculate the GCB waveform using fast/slow TODO
    """

    def __init__(self, mass1, mass2, T_obs, DL, phi0, f0, fdot=None, fddot=None, **kwargs):
        GCBWaveform.__init__(self, mass1, mass2, T_obs, DL, phi0, f0, fdot, fddot, **kwargs)
        self.N = N

    def biffersoze(self, f, oversample=1):
        mult = 8
        rr = self.T_obs/YRSID_SI
        if rr <= 8.0: mult = 8
        if rr <= 4.0: mult = 4
        if rr <= 2.0: mult = 2
        if rr <= 1.0: mult = 1

        N = 32 * mult

        if f > 0.001: N = 64*mult
        if f > 0.01: N = 256*mult
        if f > 0.03: N = 512*mult
        if f > 0.1: N = 1024*mult

        return N*oversample

    def onefourier(self, buffer=None, oversample=1):
        N = self.buffer(self.f0, oversample)
        

waveforms = {'burst': BurstWaveform,
             'bhb_PhenomD': BHBWaveform,
             'bhb_EccFD': BHBWaveformEcc,
             'gcb': GCBWaveform,
             'gcb_fast': FastGB,
             'emri': EMRIWaveform,
             }  # all available waveforms