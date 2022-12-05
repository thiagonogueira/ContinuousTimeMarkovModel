import unittest
from scipy.stats import logistic
import numpy as np
from theano.tensor import as_tensor_variable
from pymc3 import Model, sample, Metropolis, Dirichlet, Potential, Binomial, Beta, Slice
import theano.tensor as TT
from ContinuousTimeMarkovModel.distributions import *
from ContinuousTimeMarkovModel.samplers.forwardS import *
from ContinuousTimeMarkovModel.samplers.forwardX import *
from theano import function
from pickle import load

class logpTests(unittest.TestCase):
    def setUp(self):
        #test Claims
        N = 100 # Number of patients
        M = 6 # Number of hidden states
        K = 10 # Number of comorbidities
        D = 721 # Number of claims
        Dd = 80 # Maximum number of claims that can occur at once
        min_obs = 10 # Minimum number of observed claims per patient
        max_obs = 30 # Maximum number of observed claims per patient
        self.M = M
        self.N = N
        self.K = K
        # Load pre-generated data
        from pickle import load

        T = load(open('../../data/X_layer_100_patients_old/T.pkl', 'rb'))
        self.T = T
        obs_jumps = load(open('../../data/X_layer_100_patients_old/obs_jumps.pkl', 'rb'))
        S_start = load(open('../../data/X_layer_100_patients_old/S.pkl', 'rb'))
        X_start = load(open('../../data/X_layer_100_patients_old/X.pkl', 'rb'))
        Z_start = load(open('../../data/X_layer_100_patients_old/Z.pkl', 'rb'))
        L_start = load(open('../../data/X_layer_100_patients_old/L.pkl', 'rb'))
        O = load(open('../../data/X_layer_100_patients_old/O_input.pkl', 'rb'))

        self.nObs = nObs = T.sum()
        self.zeroIndices = np.roll(self.T.cumsum(),1)
        self.zeroIndices[0] = 0
        obs_jumps = np.hstack([np.zeros((N,1),dtype='int8'),obs_jumps])
        obs_jumps = np.concatenate([obs_jumps[i,0:T[i]] for i in range(N)])
        O = np.concatenate([O[:,0:T[i],i].T for i in range(N)])
        S_start = np.concatenate([S_start[i,0:T[i]] for i in range(N)])
        X_start = np.concatenate([X_start[:,0:T[i],i].T for i in range(N)])
        anchors = []
        self.Z_original
        mask = np.ones((K,D))
        for anchor in anchors:
            for hold in anchor[1]:
                mask[:,hold] = 0
                mask[anchor[0],hold] = 1
        Z_start = Z_start[mask.nonzero()]

        with Model() as self.model:
            self.pi = Dirichlet('pi', a = as_tensor_variable([0.5,0.5,0.5,0.5,0.5,0.5]), shape=M)
            pi_min_potential = Potential('pi_min_potential', TT.switch(TT.min(self.pi) < .1, -np.inf, 0))
            self.Q = DiscreteObsMJP_unif_prior('Q', M=M, lower=0.0, upper=1.0, shape=(M,M))
            self.S = DiscreteObsMJP('S', pi=self.pi, Q=self.Q, M=M, nObs=nObs, observed_jumps=obs_jumps, T=T, shape=(nObs))
            self.B0 = Beta('B0', alpha = 1., beta = 1., shape=(K,M))
            self.B = Beta('B', alpha = 1., beta = 1., shape=(K,M))
            self.X = Comorbidities('X', S=self.S, B0=self.B0,B=self.B, T=T, shape=(nObs,K))
            #self.Z = Beta('Z', alpha = 0.1, beta = 1., shape=(K,D))
            self.Z = Beta_with_anchors('Z', anchors=anchors, K=K, D=D, alpha = 0.1, beta = 1., shape=(K,D))
            self.L = Beta('L', alpha = 1., beta = 1., shape=D)
            self.testClaims = Claims('O_obs', X=self.X, Z=self.Z, L=self.L, T=T, D=D, O_input=O, shape=(nObs,Dd), observed=O)

            self.forS = ForwardS(vars=[self.S], N=N, T=T, nObs=nObs, observed_jumps=obs_jumps)
            self.forX = ForwardX(vars=[self.X], N=N, T=T, K=K, D=D,Dd=Dd, O=O, nObs=nObs)

        from scipy.special import logit

        self.Q_raw_log = logit(np.array([0.631921, 0.229485, 0.450538, 0.206042, 0.609582]))

        B_lo = logit(np.array([
        [0.000001,0.760000,0.720000,0.570000,0.700000,0.610000],
        [0.000001,0.460000,0.390000,0.220000,0.200000,0.140000],
        [0.000001,0.620000,0.620000,0.440000,0.390000,0.240000],
        [0.000001,0.270000,0.210000,0.170000,0.190000,0.070000],
        [0.000001,0.490000,0.340000,0.220000,0.160000,0.090000],
        [0.000001,0.620000,0.340000,0.320000,0.240000,0.120000],
        [0.000001,0.550000,0.390000,0.320000,0.290000,0.150000],
        [0.000001,0.420000,0.240000,0.170000,0.170000,0.110000],
        [0.000001,0.310000,0.300000,0.230000,0.190000,0.110000],
        [0.000001,0.470000,0.340000,0.190000,0.190000,0.110000]]))

        B0_lo = logit(np.array([
        [0.410412,0.410412,0.418293,0.418293,0.429890,0.429890],
        [0.240983,0.240983,0.240983,0.240983,0.240983,0.240983],
        [0.339714,0.339714,0.339714,0.339714,0.339714,0.339714],
        [0.130415,0.130415,0.130415,0.130415,0.130415,0.130415],
        [0.143260,0.143260,0.143260,0.143260,0.143260,0.143260],
        [0.211465,0.211465,0.211465,0.211465,0.211465,0.211465],
        [0.194187,0.194187,0.194187,0.194187,0.194187,0.194187],
        [0.185422,0.185422,0.185422,0.185422,0.185422,0.185422],
        [0.171973,0.171973,0.171973,0.171973,0.171973,0.171973],
        [0.152277,0.152277,0.152277,0.152277,0.152277,0.152277]]))

        Z_lo = logit(Z_start)
        L_lo = logit(L_start)
        #import pdb; pdb.set_trace()
        self.myTestPoint = {'Q_ratematrixoneway': self.Q_raw_log, 'B_logodds':B_lo, 'B0_logodds':B0_lo, 'S':S_start, 'X':X_start, 'Z_anchoredbeta':Z_lo, 'L_logodds':L_lo, 'pi_stickbreaking':np.array([0.5,0.5,0.5,0.5,0.5,0.5])}

#    def test_claims_pi_same_as_old(self):
#        pi_LL = self.pi.transformed.logp(self.myTestPoint)
#        pi_LL_Correct = -3.493851901732915
#        np.testing.assert_almost_equal(pi_LL, pi_LL_Correct, decimal = 6, err_msg="logp of pi is incorrect")

    def test_claims_Q_same_as_old(self):
        with self.model:
            Q_LL = self.Q.transformed.logp(self.myTestPoint)
            Q_LL_Correct = -7.833109951183136
            np.testing.assert_almost_equal(Q_LL, Q_LL_Correct, decimal = 6, err_msg="logp of Q is incorrect")

    def test_claims_S_same_as_old(self):
        with self.model:
            S_LL = self.S.logp(self.myTestPoint)
            S_LL_Correct = -602.4680678270764
            np.testing.assert_almost_equal(S_LL, S_LL_Correct, decimal = 6, err_msg="logp of S is incorrect")

    def test_claims_B0_same_as_old(self):
        with self.model:
            B0_LL = self.B0.transformed.logp(self.myTestPoint)
            B0_LL_Correct = -110.48096505515802
            np.testing.assert_almost_equal(B0_LL, B0_LL_Correct, decimal = 6, err_msg="logp of B0 is incorrect")

    def test_claims_B_same_as_old(self):
        with self.model:
            B_LL = self.B.transformed.logp(self.myTestPoint)
            B_LL_Correct = -224.71212579379755
            np.testing.assert_almost_equal(B_LL, B_LL_Correct, decimal = 6, err_msg="logp of B is incorrect")

    def test_claims_Z_same_as_old(self):
        with self.model:
            Z_LL = self.Z.transformed.logp(self.myTestPoint)
            Z_LL_Correct = -21916.630568050998
            np.testing.assert_almost_equal(Z_LL, Z_LL_Correct, decimal = 6, err_msg="logp of Z is incorrect")

    def test_claims_X_same_as_old(self):
        with self.model:
            X_LL = self.X.logp(self.myTestPoint)
            X_LL_Correct = -1069.7455676992997
            np.testing.assert_almost_equal(X_LL, X_LL_Correct, decimal = 6, err_msg="logp of X is incorrect")

    def test_claims_L_same_as_old(self):
        with self.model:
            L_LL = self.L.transformed.logp(self.myTestPoint)
            L_LL_Correct = -5461.275093993832
            np.testing.assert_almost_equal(L_LL, L_LL_Correct, decimal = 6, err_msg="logp of O is incorrect")

    def test_claims_O_same_as_old(self):
        with self.model:
            claims_LL = self.testClaims.logp(self.myTestPoint)
            claims_LL_Correct = -227668.7133875753
            #defaultVal = self.testClaims.logp(self.model.test_point)
            #defaultCorrect = -2280947.613994252

            np.testing.assert_almost_equal(claims_LL, claims_LL_Correct, decimal = 6, err_msg="logp of O is incorrect")
            #np.testing.assert_almost_equal(defaultVal, defaultCorrect, decimal = 6, err_msg="logp of O is incorrect for default input")

#    def test_forwardS_same_as_old(self):
#        self.forS.astep(0.)
#        pS0_Test = self.forS.compute_S0_GIVEN_X0()
#        #pS_Test = self.forS.compute_pS(Qtest,self.M)
#        pS0_Correct = load(open('pS0_Test_data.pkl', 'rb'))
#
#        pSnt_Test = np.zeros((self.N,self.max_obs,self.M))
#        for n in range(self.N):
#            for t in range(self.T[n]-1):
#                pSnt_Test[n,t] = self.forS.compute_pSt_GIVEN_St1(n,t,self.myTestPoint['S'][n,t])
#        pSnt_Correct = load(open('pSnt_Test_data.pkl', 'rb'))
#
#        #import pdb; pdb.set_trace()
#        np.testing.assert_array_almost_equal(pS0_Test, pS0_Correct, err_msg="forwardS test off",decimal = 6)
#        np.testing.assert_array_almost_equal(pSnt_Test, pSnt_Correct, err_msg="forwardS test off",decimal = 6)
    def test_forwardS_same_as_old(self):
        self.forS.astep(0.)
        pS0_Test = self.forS.compute_S0_GIVEN_X0(self.forS.computeLikelihoodOfS(self.myTestPoint['X'],logistic.cdf(self.myTestPoint['B_logodds']),logistic.cdf(self.myTestPoint['B0_logodds'])))
        pS0_Correct = load(open('pS0_Test_data.pkl', 'rb'))

        pSnt_Test = np.zeros((self.nObs,self.M))
        for n in range(self.N):
            n0 = self.zeroIndices[n]
            for t in range(self.T[n]-1):
                pSnt_Test[n0+t] = self.forS.compute_pSt_GIVEN_St1(n0,t,self.myTestPoint['S'][n0+t])
        pSnt_Test = pSnt_Test / pSnt_Test.sum(axis=1)[:,np.newaxis]
        pSnt_Correct = load(open('pSnt_Test_data.pkl', 'rb'))
        pSnt_Correct = np.concatenate([pSnt_Correct[i,0:self.T[i],:] for i in range(self.N)])
        pSnt_Correct = pSnt_Correct / pSnt_Correct.sum(axis=1)[:,np.newaxis]

        #import pdb; pdb.set_trace()
        np.testing.assert_array_almost_equal(pS0_Test, pS0_Correct, err_msg="forwardS test off",decimal = 6)
        np.testing.assert_array_almost_equal(pSnt_Test, pSnt_Correct, err_msg="forwardS test off",decimal = 6)


    def test_forwardX_same_as_old(self):
        Psi = self.forX.computePsi(self.myTestPoint['S'],logistic.cdf(self.myTestPoint['B_logodds']))
        LikelihoodOfX = self.forX.computeLikelihoodOfX(self.myTestPoint['X'],self.Z_original,logistic.cdf(self.myTestPoint['L_logodds']))
        beta = self.forX.computeBeta(Psi,LikelihoodOfX)
        pX_Test = self.forX.computePX(beta,logistic.cdf(self.myTestPoint['B0_logodds']),self.myTestPoint['S'],self.myTestPoint['X'],LikelihoodOfX,Psi)
        pX_Test = pX_Test[:,:,0] / (pX_Test[:,:,0]+pX_Test[:,:,1])
        pX_Correct = load(open('pX_Test_data.pkl','rb'))
        pX_Correct = np.concatenate([pX_Correct[i,0:self.T[i],:,:] for i in range(self.N)])
        pX_Correct = pX_Correct[:,:,0] / (pX_Correct[:,:,0]+pX_Correct[:,:,1])
        #import pdb; pdb.set_trace()
        np.testing.assert_array_almost_equal(pX_Test, pX_Correct, err_msg="forwardX likelihood test off",decimal = 6)

if __name__ == '__main__':
    unittest.main()
