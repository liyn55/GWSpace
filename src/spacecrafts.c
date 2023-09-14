#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#include "spacecrafts.h"
#include "Constants.h"

void instrument_noise(double f, double *SAE, double *SXYZ)
{
    //Power spectral density of the detector noise and transfer frequency
    double red, Sloc;
    double trans;
        
    red  = 16.0*(pow((2.0e-5/f), 10.0)+ (1.0e-4/f)*(1.0e-4/f));
    Sloc = 2.89e-24;
    
    // Calculate the power spectral density of the detector noise at the given frequency
    trans = pow(sin(f/fstar), 2.0);
    
    *SAE = 16.0/3.0*trans*( (2.0+cos(f/fstar))*(Sps + Sloc) 
    					    +2.0*( 3.0 + 2.0*cos(f/fstar) + cos(2.0*f/fstar) )
    					        *( Sloc/2.0 + Sacc/pow(2.0*PI*f,4.0)*(1.0+red) ) )
    					  / pow(2.0*Larm,2.0);
    
    *SXYZ = 4.0*trans*( 4.0*(Sps+Sloc) 
                      + 8.0*( 1.0+pow(cos(f/fstar),2.0) )*( Sloc/2.0 + Sacc/pow(2.0*PI*f,4.0)*(1.0+red) ) )
                       / pow(2.0*Larm,2.0);
    
    return;
}

void spacecraft_LISA(double t, double *x, double *y, double *z)
{
	double alpha;
	double beta1, beta2, beta3;
	double sa, sb, ca, cb;

	alpha = 2.*PI*fm*t + kappa;

	beta1 = 0. + lambda;
	beta2 = 2.*PI/3. + lambda;
	beta3 = 4.*PI/3. + lambda;

	sa = sin(alpha);
	ca = cos(alpha);

	sb = sin(beta1);
	cb = cos(beta1);
	x[0] = AU*ca + AU*ec*(sa*ca*sb - (1. + sa*sa)*cb);
	y[0] = AU*sa + AU*ec*(sa*ca*cb - (1. + ca*ca)*sb);
	z[0] = -SQ3*AU*ec*(ca*cb + sa*sb);

	sb = sin(beta2);
	cb = cos(beta2);
	x[1] = AU*ca + AU*ec*(sa*ca*sb - (1. + sa*sa)*cb);
	y[1] = AU*sa + AU*ec*(sa*ca*cb - (1. + ca*ca)*sb);
	z[1] = -SQ3*AU*ec*(ca*cb + sa*sb);

	sb = sin(beta3);
	cb = cos(beta3);
	x[2] = AU*ca + AU*ec*(sa*ca*sb - (1. + sa*sa)*cb);
	y[2] = AU*sa + AU*ec*(sa*ca*cb - (1. + ca*ca)*sb);
	z[2] = -SQ3*AU*ec*(ca*cb + sa*sb);

	return;
}

void spacecraft_TianQin(double t, double *x, double *y, double *z)
{
    // earth position
    // kappa_earth = LISA + 20 
    double alpha = EarthOrbitOmega_SI * t + kappa + 0.3490658503988659;
    double beta = Perihelion_Ang;
    double sna = sin(alpha - beta);
    double csa = cos(alpha - beta);
    double ecc = EarthEccentricity;
    double ecc2 = ecc*ecc;

    double x_earth = AU *( csa + ecc * (1+sna*sna) - 1.5*ecc2 * csa*sna*sna);
    double y_earth = AU * (sna + ecc *sna*csa + 0.5*ecc2 * sna*(1-3*sna*sna));
    double z_earth = 0.0;
    
    //TianQin orbit function
    //calculate alpha_n
    double alpha_tq = Omega_tq * t + lambda_tq;
    
    double sp = sin(J0806_phi);
    double cp = cos(J0806_phi);
    double st = sin(J0806_theta);
    double ct = cos(J0806_theta);

    for (int i=0; i<3; i++){
        alpha = alpha_tq + i * 2.*PI/3.;
        csa = cos(alpha); sna = sin(alpha);

        x[i] = ct * cp * sna + sp * csa;
        y[i] = ct * sp * sna - cp * csa;
        z[i] = - st * sna;

        x[i] *= Radius_tq; y[i] *= Radius_tq; z[i] *= Radius_tq;
        x[i] += x_earth; y[i] += y_earth; z[i] += z_earth;
    }

    return;
}