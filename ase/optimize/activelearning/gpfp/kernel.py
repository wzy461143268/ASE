import numpy as np
import numpy.linalg as la
from ase.parallel import world


class Kernel():
    def __init__(self):
        pass

    def set_params(self, params):
        pass

    def kernel(self, x1, x2):
        '''Kernel function to be fed to the Kernel matrix'''
        pass

    def K(self, X1, X2):
        '''Compute the kernel matrix '''
        return np.block([[self.kernel(x1, x2) for x2 in X2] for x1 in X1])


class SE_kernel(Kernel):
    '''Squared exponential kernel without derivatives '''

    def __init__(self):
        Kernel.__init__(self)

    def set_params(self, params):
        '''Set the parameters of the squared exponential kernel.

        Parameters:

        params: [weight, l] Parameters of the kernel:
            weight: prefactor of the exponential
            l : scale of the kernel
            '''

        self.weight = params[0]
        self.l = params[1]

    def squared_distance(self, x1, x2):
        '''Returns the norm of x1-x2 using diag(l) as metric '''
        return np.linalg.norm(x1 - x2)**2 / self.l**2

    def kernel(self, x1, x2):
        ''' This is the squared exponential function'''
        return self.weight**2 * np.exp(-0.5 * self.squared_distance(x1, x2))

    def dK_dweight(self, x1, x2):
        '''Derivative of the kernel respect to the weight '''
        return 2 * self.weight * np.exp(-0.5 * self.squared_distance(x1, x2))

    def dK_dl(self, x1, x2):
        '''Derivative of the kernel respect to the scale'''
        return self.kernel * la.norm(x1 - x2)**2 / self.l**3

    def kernel_matrix(self, X):
        return self.K(X, X)

    def kernel_vector(self, x, X, nsample):
        return np.hstack([self.kernel(x, x2) for x2 in X])


class SquaredExponential(SE_kernel):
    '''Squared exponential kernel with derivatives.
    For the formulas, see Koistinen, Dagbjartssdittir, Asgeirsson, Vehtari, Jonsson,
    Nudged elastic band calculations accelerated with Gaussian process regression.
    section 3.

    Before making any predictions, the parameters need to be set using the method
    SquaredExponential.set_params(params) with the parameters being a list whose
    first entry is the weight (prefactor of the exponential) and the second being
    the scale (l)

    Parameters:

    dimensionality: The dimensionality of the problem to optimize, tipically, 3*N with
        N being the number of atoms. If dimensionality =None, it is computed when the kernel
        method is called.



    Atributes:
    ----------------
    D:          int. Dimensionality of the problem to optimize
    weight:     float. Multiplicative constant to the exponenetial kernel
    l :         float. Lenght scale of the squared exponential kernel

    Relevant Methods:
    ----------------
    set_params:                 Set the parameters of the Kernel, i.e. change the atributes
    kernel_function:    squared exponential covariance function
    kernel:             covariance matrix between two points in the manifold.
                            Note the inputs are arrays of shape (D,)
    kernel_matrix:      kernel matrix of a data set to itself, K(X,X)
                            Note the input is an array of shape (nsamples, D)
    kernel_vector       kernel matrix of a point x to a dataset X, K(x,X).

    gradient:           Gradient of K(X,X) with respect to the parameters of the kernel
                            i.e. the hyperparameters of the Gaussian process.
    '''

    def __init__(self, dimensionality=None):
        self.D = dimensionality
        SE_kernel.__init__(self)

    def kernel_function(self, x1, x2):
        ''' This is the squared exponential function'''
        return self.weight**2 * np.exp(-0.5 * self.squared_distance(x1, x2))

    def kernel_function_gradient(self, x1, x2):
        '''Gradient of kernel_function respect to the second entry.
        x1: first data point
        x2: second data point'''

        prefactor = (x1 - x2) / self.l**2
        # return prefactor * self.kernel_function(x1,x2)
        return prefactor

    def kernel_function_hessian(self, x1, x2):
        '''Second derivatives matrix of the kernel function '''

        P = np.outer(x1 - x2, x1 - x2) / self.l**2
        prefactor = (np.identity(self.D) - P) / self.l**2

        return prefactor

    def kernel(self, x1, x2):
        '''Squared exponential kernel including derivatives.
        This function returns a D+1 x D+1 matrix, where D is the dimension of the manifold'''

        K = np.identity(self.D + 1)
        K[0, 1:] = self.kernel_function_gradient(x1, x2)
        K[1:, 0] = -K[0, 1:]
        # K[1:,1:] = self.kernel_function_hessian(x1, x2)

        P = np.outer(x1 - x2, x1 - x2) / self.l**2
        K[1:, 1:] = (K[1:, 1:] - P) / self.l**2

        # return np.block([[k,j2],[j1,h]])*self.kernel_function(x1, x2)
        return K * self.kernel_function(x1, x2)

    def kernel_matrix(self, X):
        '''This is the same method than self.K for X1=X2, but using the matrix is then symmetric'''
        # rename parameters
        shape = X.shape
        if len(shape) > 1:
            D = shape[1]
        else:
            D = 1
        n = shape[0]
        self.D = D

        # allocate memory
        K = np.identity((n * (D + 1)), dtype=float)

        # fill upper triangular:
        for i in range(0, n):
            for j in range(i + 1, n):
                k = self.kernel(X[i, :], X[j, :])
                K[i * (D + 1):(i + 1) * (D + 1), j *
                  (D + 1):(j + 1) * (D + 1)] = k
                K[j * (D + 1):(j + 1) * (D + 1), i *
                  (D + 1):(i + 1) * (D + 1)] = k.T
            K[i * (D + 1):(i + 1) * (D + 1),
              i * (D + 1):(i + 1) * (D + 1)] = self.kernel(X[i, :], X[i, :])

        return K

    def kernel_vector(self, x, X, nsample):
        return np.hstack([self.kernel(x, x2) for x2 in X])

    # ---------Derivatives--------

    def dK_dweight(self, X):
        '''Return the derivative of K(X,X) respect to the weight '''
        return self.K(X, X) * 2 / self.weight

    # ----Derivatives of the kernel function respect to the scale ---
    def dK_dl_k(self, x1, x2):
        '''Returns the derivative of the kernel function respect to  l
        '''
        return self.squared_distance(x1, x2) / self.l

    def dK_dl_j(self, x1, x2):
        '''Returns the derivative of the gradient of the kernel
        function respect to l'''
        prefactor = -2 * (1 - 0.5 * self.squared_distance(x1, x2)) / self.l
        return self.kernel_function_gradient(x1, x2) * prefactor

    def dK_dl_h(self, x1, x2):
        '''Returns the derivative of the hessian of the kernel
        function respect to l'''
        I = np.identity(self.D)
        P = np.outer(x1 - x2, x1 - x2) / self.l**2
        prefactor = 1 - 0.5 * self.squared_distance(x1, x2)

        return -2 * (prefactor * (I - P) - P) / self.l**3

    def dK_dl_matrix(self, x1, x2):

        k = np.asarray(self.dK_dl_k(x1, x2)).reshape((1, 1))
        j2 = self.dK_dl_j(x1, x2).reshape(1, -1)
        j1 = self.dK_dl_j(x2, x1).reshape(-1, 1)
        h = self.dK_dl_h(x1, x2)

        return np.block([[k, j2], [j1, h]]) * self.kernel_function(x1, x2)

    def dK_dl(self, X):
        '''Return the derivative of K(X,X) respect of l '''

        return np.block([[self.dK_dl_matrix(x1, x2) for x2 in X] for x1 in X])

    def gradient(self, X):
        '''Computes the gradient of matrix K given the data respect to the hyperparameters
        Note matrix K here is self.K(X,X)

        returns a 2-entry list of n(D+1) x n(D+1) matrices '''

        g = [self.dK_dweight(X), self.dK_dl(X)]

        return g


class FPKernel(SE_kernel):

    def __init__(self):
        SE_kernel.__init__(self)

    def kernel_function_gradient(self, x1, x2):
        '''Gradient of kernel_function respect to the second entry.
        x1: first data point
        x2: second data point'''

        n = len(x1.atoms)
        gradients = np.empty([n, 3])

        # Distribute calculations for processors:
        myatoms = []
        for k in range(n):
            if (k % world.size) == world.rank:
                myatoms.append(k)

        # Calculate:
        for i in myatoms:
            gradients[i] = x1.kernel_gradient(x2, i)

        # Share data among processors:
        for i in range(n):
            world.broadcast(gradients[i], i % world.size)

        return gradients.reshape(-1)

    def kernel_function_hessian(self, x1, x2):
        d = 3
        hessian = np.zeros([len(x1.atoms), len(x2.atoms), d, d])
        n = len(x1.atoms)

        for i in range(len(x1.atoms)):
            for j in range(len(x2.atoms)):
                if ((i * n + j) % world.size) == world.rank:
                    hessian[i, j] = x1.kernel_hessian(x2, i, j)

        # Share data among processors:
        for i in range(n):
            for j in range(len(x2.atoms)):
                world.broadcast(hessian[i, j], (i * n + j) % world.size)

        # Reshape to 2D matrix:
        hessian = hessian.swapaxes(1, 2).reshape(d * len(x1.atoms),
                                                 d * len(x2.atoms))

        return hessian

    def set_fp_params(self, x):

        if self.params != x.params:
            x.update(self.params)

    def kernel(self, x1, x2):
        '''Squared exponential kernel including derivatives.
        This function returns a D+1 x D+1 matrix, where D is
        the dimension of the manifold'''

        K = np.identity(self.D + 1)

        K[0, 0] = x1.kernel(x1, x2)
        K[1:, 0] = self.kernel_function_gradient(x1, x2)
        K[0, 1:] = self.kernel_function_gradient(x2, x1)
        K[1:, 1:] = self.kernel_function_hessian(x1, x2)

        return K * self.params.get('weight')**2

    def kernel_matrix(self, X):
        ''' Calculates K(X,X) ie. kernel matrix for training data. '''

        D = len(X[0].atoms) * 3
        n = len(X)
        self.D = D

        # allocate memory
        K = np.identity((n * (D + 1)), dtype=float)

        for x in X:
            self.set_fp_params(x)

        for i in range(0, n):
            for j in range(i + 1, n):
                k = self.kernel(X[i], X[j])
                K[i * (D + 1):(i + 1) * (D + 1), j *
                  (D + 1):(j + 1) * (D + 1)] = k
                K[j * (D + 1):(j + 1) * (D + 1), i *
                  (D + 1):(i + 1) * (D + 1)] = k.T

            K[i * (D + 1):(i + 1) * (D + 1),
              i * (D + 1):(i + 1) * (D + 1)] = self.kernel(X[i], X[i])

        world.broadcast(K, 0)

        return K

    def kernel_vector(self, x, X):

        self.set_fp_params(x)
        for x2 in X:
            self.set_fp_params(x2)

        return np.hstack([self.kernel(x, x2) for x2 in X])

        # ---------Derivatives--------

    def set_params(self, params):

        if not hasattr(self, 'params'):
            self.params = {}

        for p in params:
            self.params[p] = params[p]

    def dK_dweight(self, X):
        '''Return the derivative of K(X,X) respect to the weight '''

        return self.kernel_matrix(X) * 2 / self.weight

    # ----Derivatives of the kernel function respect to the scale ---
    def dK_dl_k(self, x1, x2):
        '''Returns the derivative of the kernel function respect to  l
        '''

        return x1.dk_dl(x2)

    def dK_dl_j(self, x1, x2):
        '''Returns the derivative of the gradient of the kernel
        function respect to l'''

        vector = np.ndarray([len(x1.atoms), 3])
        for atom in x1.atoms:
            vector[atom.index] = x1.d_dl_dk_drm(x2, atom.index)
        return vector.reshape(-1)

    def dK_dl_h(self, x1, x2):
        '''Returns the derivative of the hessian of the kernel
        function respect to l'''

        d = 3
        matrix = np.ndarray([d * len(x1.atoms), d * len(x2.atoms)])

        for i in range(len(x1.atoms)):
            for j in range(len(x2.atoms)):
                matrix[i * d:(i + 1) * d,
                       j * d:(j + 1) * d] = x1.d_dl_dk_drm_drn(x2, i, j)

        return matrix

    def dK_dl_matrix(self, x1, x2):

        matrix = np.ndarray([self.D + 1, self.D + 1])

        matrix[0, 0] = self.dK_dl_k(x1, x2)
        matrix[1:, 0] = self.dK_dl_j(x1, x2)
        matrix[0, 1:] = self.dK_dl_j(x2, x1)
        matrix[1:, 1:] = self.dK_dl_h(x1, x2)

        return matrix * self.weight**2

    def dK_dl(self, X):
        '''Return the derivative of K(X,X) respect of l '''

        return np.block([[self.dK_dl_matrix(x1, x2)
                          for x2 in X]
                         for x1 in X])

    # Derivatives w.r.t. Delta:

    def dK_dDelta_k(self, x1, x2):
        '''Returns the derivative of the kernel function respect to Delta
        '''
        return x1.dk_dDelta(x2)

    def dK_dDelta_j(self, x1, x2):
        '''Returns the derivative of the gradient of the kernel
        function respect to Delta'''

        vector = np.zeros([len(x1.atoms), 3])
        for atom in x1.atoms:
            vector[atom.index] = x1.dk_drm_dDelta(x2, atom.index)
        return vector.reshape(-1)

    def dK_dDelta_h(self, x1, x2):
        '''Returns the derivative of the hessian of the kernel
        function respect to Delta'''

        d = 3
        matrix = np.zeros([d * len(x1.atoms), d * len(x2.atoms)])

        for i in range(len(x1.atoms)):
            for j in range(len(x2.atoms)):
                matrix[i * d:(i + 1) * d,
                       j * d:(j + 1) * d] = x1.dk_drm_drn_dDelta(x2, i, j)

        return matrix

    def dK_dDelta_matrix(self, x1, x2):

        matrix = np.ndarray([self.D + 1, self.D + 1])

        matrix[0, 0] = self.dK_dDelta_k(x1, x2)
        matrix[1:, 0] = self.dK_dDelta_j(x1, x2)
        matrix[0, 1:] = self.dK_dDelta_j(x2, x1)
        matrix[1:, 1:] = self.dK_dDelta_h(x1, x2)

        return matrix * self.weight**2

    def dK_dDelta(self, X):
        '''Return the derivative of K(X,X) respect of l '''

        return np.block([[self.dK_dDelta_matrix(x1, x2)
                          for x2 in X]
                         for x1 in X])

    def gradient(self, X):
        '''Computes the gradient of matrix K given the data
        w.r.t the hyperparameters
        Note matrix K here is self.K(X,X)

        returns a 3-entry list of n(D+1) x n(D+1) matrices '''

        for x in X:
            self.set_fp_params(x)

        g = [self.dK_dweight(X), self.dK_dl(X), self.dK_dDelta(X)]

        return g


class FPKernelNoforces(FPKernel):

    def __init__(self):
        """
        Squared exponential kernel with fingerprints but without
        forces
        """
        FPKernel.__init__(self)


    def kernel(self, x1, x2):
        K = x1.kernel(x1, x2)
        return np.atleast_1d(K) * self.params.get('weight')**2


    def kernel_matrix(self, X):
        ''' Calculates K(X,X) ie. kernel matrix for training data. '''
        n = len(X)

        # allocate memory
        K = np.identity(n, dtype=float)

        for x in X:
            self.set_fp_params(x)

        for i in range(0, n):
            for j in range(i+1, n):
                k = self.kernel(X[i], X[j])
                K[i:(i+1), j:(j+1)] = k
                K[j:(j+1), i:(i+1)] = k.T

            K[i:(i+1), 
              i:(i+1)] = self.kernel(X[i], X[i])

        assert (K == K.T).all()
        return K


    def kernel_vector(self, x, X):

        self.set_fp_params(x)
        for x2 in X:
            self.set_fp_params(x2)

        return np.hstack([self.kernel(x, x2) for x2 in X])

