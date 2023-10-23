import numpy as np

from gwspace.constants import YRSID_SI
from gwspace.wrap import FrequencyArray

if __package__ or "." in __name__:
    from gwspace import libFastGB
else:
    import libFastGB


class FastGB:
    # FastBinaryCache = {}
    def __init__(self, dt=15.0, Tobs=6.2914560e7, detector="TianQin"):

        self.Tobs = Tobs
        self.dt = dt
        self.detector = detector

    def buffersize(self, f, A, algorithm='ldc', oversample=1):
        YEAR = YRSID_SI
        # Acut = simplesnr(f,A,years=self.Tobs/YEAR)
        mult = 8
        if (self.Tobs/YEAR) <= 8.0: mult = 8
        if (self.Tobs/YEAR) <= 4.0: mult = 4
        if (self.Tobs/YEAR) <= 2.0: mult = 2
        if (self.Tobs/YEAR) <= 1.0: mult = 1
        N = 32*mult
        if f > 0.001: N = 64*mult
        if f > 0.01:  N = 256*mult
        if f > 0.03:  N = 512*mult
        if f > 0.1:   N = 1024*mult

        # M = int(math.pow(2.0,1 + int(np.log(Acut)/np.log(2.0))))

        # if(M > 8192):
        #  M = 8192
        # M = 8192

        # M = N = max(M,N)

        N *= oversample

        return N

    def onefourier(self, simulator='synthlisa', params=None, buffer=None, T=6.2914560e7, dt=15., algorithm='mldc',
                   oversample=1):
        if np.any(params) is not None:
            self.Frequency, self.FrequencyDerivative, self.Amplitude = params[0], params[1], params[4]

        # FIXME I assume that T=Tobs below
        if T != self.Tobs:
            print("times do not match:", T, self.Tobs)
            raise NotImplementedError
        N = self.buffersize(self.Frequency, self.Amplitude, algorithm, oversample)
        M = N

        XLS = np.zeros(2*M, 'd')
        YLS = np.zeros(2*M, 'd')
        ZLS = np.zeros(2*M, 'd')

        XSL = np.zeros(2*M, 'd')
        YSL = np.zeros(2*M, 'd')
        ZSL = np.zeros(2*M, 'd')

        # TestMe(XLS)

        if np.any(params) is not None:
            NP = 8
            # vector must be ordered as required by Fast_GB
            # Fast_GB(double *params, long N, double *XLS, double *ALS, double *ELS, int NP)

            # ComputeXYZ_FD(params, N, self.Tobs, self.dt, XLS, YLS, ZLS, XSL, YSL, ZSL, self.detector)
            libFastGB.ComputeXYZ_FD(params, N, T, dt, XLS, YLS, ZLS, XSL, YSL, ZSL, len(params), detector=self.detector)
            # TODO Need to transform to SL if required
            Xf = XLS
            Yf = YLS
            Zf = ZLS
            if simulator == 'synthlisa':
                Xf = XSL
                Yf = YSL
                Zf = ZSL
        else:
            # FIXME
            raise NotImplementedError

        f0 = self.Frequency
        # f0 = self.Frequency + 0.5 * self.FrequencyDerivative * T
        if buffer is None:
            retX, retY, retZ = map(lambda a: FrequencyArray(a[::2]+1.j*a[1::2],
                                                            dtype=np.complex128, kmin=int(f0*T)-M/2, df=1.0/T),
                                   (Xf, Yf, Zf))
            return retX, retY, retZ
        else:
            kmin, blen, alen = buffer[0].kmin, len(buffer[0]), 2*M
            # print ("herak", kmin, blen, alen, len(Xf))

            beg, end = int(int(f0*T)-M/2), int(f0*T+M/2)  # for a full buffer, "a" begins and ends at these indices
            begb, bega = (beg-kmin, 0) if beg >= kmin else (
                0, 2*(kmin-beg))  # left-side alignment of partial buffer with "a"
            endb, enda = (end-kmin, alen) if end-kmin <= blen else (blen, alen-2*(end-kmin-blen))
            # the corresponding part of "a" that should be assigned to the partial buffer
            # ...remember "a" is doubled up
            # check: if kmin = 0, then begb = beg, endb = end, bega = 0, enda = alen
            bega = int(bega)
            begb = int(begb)
            enda = int(enda)
            endb = int(endb)
            for i, a in enumerate((Xf, Yf, Zf)):
                buffer[i][begb:endb] += a[bega:enda:2]+1j*a[(bega+1):enda:2]

    def fourier(self, simulator='synthlisa', table=None, T=6.2914560e7, dt=15., algorithm='mldc', oversample=1, kmin=0,
                length=None):
        if np.any(table) is None:
            return self.onefourier(simulator=simulator, T=T, dt=dt, algorithm=algorithm, oversample=oversample)
        else:
            if length is None:
                length = int(0.5*T/dt)+1  # was "NFFT = int(T/dt)", and "NFFT/2+1" passed to numpy.zeros

            # length = int(length)
            # print ("Stas", type(length), type(kmin), type(1.0/T))
            buf = tuple(FrequencyArray(np.zeros(length, dtype=np.complex128), kmin=kmin, df=1.0/T) for _ in range(3))

            for line in table:
                self.onefourier(simulator=simulator, params=line, buffer=buf, T=T, dt=dt, algorithm=algorithm,
                                oversample=oversample)
                if status:
                    c.status()
            if status:
                c.end()

            return buf

    def TDI(self, T=6.2914560e7, dt=15.0, simulator='synthlisa', table=None, algorithm='mldc', oversample=1):
        X, Y, Z = self.fourier(simulator, table, T=T, dt=dt, algorithm=algorithm, oversample=oversample)

        return X.ifft(dt), Y.ifft(dt), Z.ifft(dt)
