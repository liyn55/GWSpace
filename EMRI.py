#!/usr/bin/env python
#-*- coding: utf-8 -*-  
#==================================
# File Name: EMRI.py
# Author: ekli
# Mail: lekf123@163.com
# Created Time: 2023-08-28 13:43:30
#==================================

import numpy as np
from Constants import *

import sys, os
try:
    import bbh
except:
    few_path = './Waveforms/FastEMRIWaveforms'
    abs_few_path = os.path.abspath(few_path)
    
    if abs_few_path not in sys.path:
        sys.path.append(abs_few_path)

from FastEMRI import *


class EMRIWaveform:
    '''
    This is waveform for EMRI
    --------------------------
    Parameters:
    - M (double): Mass of larger black hole in solar masses.
    - mu (double): Mass of compact object in solar masses.
    - a (double): Dimensionless spin of massive black hole.
    - p0 (double): Initial semilatus rectum (Must be greater than
        the separatrix at the the given e0 and x0).
        See documentation for more information on :math:`p_0<10`.
    - e0 (double): Initial eccentricity.
    - x0 (double): Initial cosine of the inclination angle.
        (:math:`x_I=\cos{I}`). This differs from :math:`Y=\cos{\iota}\equiv L_z/\sqrt{L_z^2 + Q}`
        used in the semi-relativistic formulation. When running kludge waveforms,
        :math:`x_{I,0}` will be converted to :math:`Y_0`.
    - dist (double): Luminosity distance in Gpc.
    - qS (double): Sky location polar angle in ecliptic
        coordinates.
    - phiS (double): Sky location azimuthal angle in
        ecliptic coordinates.
    - qK (double): Initial BH spin polar angle in ecliptic
        coordinates.
    - phiK (double): Initial BH spin azimuthal angle in
        ecliptic coordinates.
    - Phi_phi0 (double, optional): Initial phase for :math:`\Phi_\phi`.
        Default is 0.0.
    - Phi_theta0 (double, optional): Initial phase for :math:`\Phi_\Theta`.
        Default is 0.0.
    - Phi_r0 (double, optional): Initial phase for :math:`\Phi_r`.
        Default is 0.0.
    - *args (tuple, optional): Tuple of any extra parameters that go into the model.
    - **kwargs (dict, optional): Dictionary with kwargs for online waveform
        generation.
    '''

    def __init__(self, M, mu, a, p0, e0, x0, dist, qS, phiS, qK, phiK,
            Phi_phi0=0, Phi_theta0=0, Phi_r0=0, 
            model = "FastSchwarzschildEccentricFlux",
            model_insp = "SchwarzEccFlux",
            specific_modes=None, 
            inspiral_kwargs=inspiral_kwargs,
            amplitude_kwargs=amplitude_kwargs,
            Ylm_kwargs=Ylm_kwargs,
            sum_kwargs=sum_kwargs,
            use_gpu=use_gpu):
        
        self.M = M
        self.mu = mu
        self.a = a
        self.p0 = p0
        self.e0 = e0
        self.x0 = x0
        self.dist = dist
        
        self.qS = qS
        self.phiS = phiS
        self.qK = qK
        self.phiK = phiK
        self.Phi_phi0 = Phi_phi0
        self.Phi_theta0 = Phi_theta0
        self.Phi_r0 = Phi_r0

        self.gen_wave = GenerateEMRIWaveform(
                model,
                inspiral_kwargs=inspiral_kwargs,
                amplitude_kwargs=amplitude_kwargs,
                Ylm_kwargs=Ylm_kwargs,
                sum_kwargs=sum_kwargs,
                use_gpu=use_gpu,
                )
        self.theta, self.phi = self.gen_wave._get_viewing_angles(qS,phiS,qK,phiK) # get view angle

        # first, lets get amplitudes for a trajectory
        self.traj = EMRIInspiral(func=model_insp)
        self.ylm_gen = GetYlms(assume_positive_m=True, use_gpu=use_gpu)

    def get_harmonic_mode(self, eps = 1e-5):
        '''
        To calculate how many harmonic mode
        -----------------------------------
        Parameters:
        - eps: tolerance on mode contribution to total power 
        '''        
        t, p, e, x, Phi_phi, Phi_theta, Phi_r = self.traj(self.M, self.mu, self.a, self.p0, self.e0, 1.0)
        
        # get amplitudes along trajectory
        amp = RomanAmplitude()
        
        teuk_modes = amp(p, e)
        
        theta ,phi = self.gen_wave._get_viewing_angles(qS,phiS,qK,phiK) # get view angle
        # get ylms
        ylms = self.ylm_gen(amp.unique_l, amp.unique_m, theta, phi).copy()[amp.inverse_lm]
        
        mode_selector = ModeSelector(amp.m0mask, use_gpu=False)
        
        modeinds = [amp.l_arr, amp.m_arr, amp.n_arr]

        (teuk_modes_in, ylms_in, ls, ms, ns) = mode_selector(teuk_modes, ylms, modeinds, eps=eps)
        return (teuk_modes_in, ylms_in, ls, ms, ns)

    def __call__(self, Tobs, dt, modes=None, eps=1e-5):
        '''
        Calculate the time domain waveforms
        -----------------------------------
        Return:
        - hp, hc

        Parameters:
        - Tobs: the observation time in [year]
        - dt: sampling time in [s]
        - modes: (str or list or None)
            - If None, perform our base mode filtering with eps as the fractional accuracy on the total power. 
            - If ‘all’, it will run all modes without filtering. 
            - If a list of tuples (or lists) of mode indices (e.g. [(l1,m1,n1), (l2,m2,n2)]) is provided, 
                it will return those modes combined into a single waveform.
        - eps: Controls the fractional accuracy during mode filtering. 
            Raising this parameter will remove modes. 
            Lowering this parameter will add modes. 
            Default that gives a good overalp is 1e-5.
        '''
        h = self.gen_wave(
                self.M,
                self.mu,
                self.a,
                self.p0,
                self.e0,
                self.x0,
                self.dist,
                self.qS,
                self.phiS,
                self.qK,
                self.phiK,
                self.Phi_phi0,
                self.Phi_theta0,
                self.Phi_r0,
                T=Tobs,
                dt=dt,
                eps=eps,
                mode_selection=modes,
                )

        return (h.real, h.imag)



if __name__ == "__main__":
    print("This is a test of loading EMRI waveform")
    # parameters
    T = 0.01  # years
    dt = 15.0  # seconds

    M = 1e6
    a = 0.1  # will be ignored in Schwarzschild waveform
    mu = 1e1
    p0 = 12.0
    e0 = 0.2
    x0 = 1.0  # will be ignored in Schwarzschild waveform
    qK = 0.2  # polar spin angle
    phiK = 0.2  # azimuthal viewing angle
    qS = 0.3  # polar sky angle
    phiS = 0.3  # azimuthal viewing angle
    dist = 1.0  # distance
    Phi_phi0 = 1.0
    Phi_theta0 = 2.0
    Phi_r0 = 3.0

    emri = EMRIWaveform(M, mu, a, p0, e0, x0, dist, qS, phiS, qK, phiK,
            Phi_phi0=0, Phi_theta0=0, Phi_r0=0)

    tf = np.arange(0, T * YRSID_SI, dt)

    hp, hc = emri(T, dt)

    import matplotlib.pyplot as plt

    plt.figure()

    plt.plot(tf[:2000], hp[:2000])
    plt.plot(tf[:2000], hc[:2000])

    plt.show()
    

