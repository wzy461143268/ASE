import numpy as np
from scipy.interpolate import interpn


def cube_2d_slice(cube, u, v, o=(0, 0, 0), step=0.02,
                  size_u=(-10, 10), size_v=(-10, 10)):
    """Extract a 2D slice from a cube file using interpolation.

    Works for non-orthogonal cells.

    Parameters:

    cube: dict
        The cube dict as returned by ase.io.cube.read_cube

    u: array_like
        The first vector defining the plane

    v: array_like
        The second vector defining the plane

    o: array_like
        The origin of the plane

    step: float
        The step size of the interpolation grid in both directions

    size_u: tuple
        The size of the interpolation grid in the u direction from the origin

    size_v: tuple
        The size of the interpolation grid in the v direction from the origin

    Returns:

    X: np.ndarray
        The x coordinates of the interpolation grid

    Y: np.ndarray
        The y coordinates of the interpolation grid

    D: np.ndarray
        The interpolated data on the grid

    Examples:

    From a cube file, we can extract a 2D slice of the density along the
    the direction of the first three atoms in the file:

    >>> from ase.io.cube import read_cube
    >>> from ase.utils.cube import cube_2d_slice
    >>> cube = read_cube(open("pt111_dens.cube", 'r'))
    >>> atoms = cube['atoms']
    >>> u = atoms[1].position - atoms[0].position
    >>> v = atoms[2].position - atoms[0].position
    >>> o = atoms[0].position
    >>> X, Y, D = cube_2d_slice(cube, u, v, o, size_u=(-1, 10), size_v=(-1, 10))
    >>> #We can now plot the data directly
    >>> import matplotlib.pyplot as plt
    >>> plt.pcolormesh(X, Y, D)
    """

    cell = cube['atoms'].get_cell()

    real_step = np.linalg.norm(cube['spacing'], axis=1)

    u = np.array(u, dtype=np.float64)
    v = np.array(v, dtype=np.float64)
    o = np.array(o, dtype=np.float64)

    # We avoid some problems
    u += np.random.random(3) * 1.0e-8
    v += np.random.random(3) * 1.0e-8
    o += np.random.random(3) * 1.0e-8

    lengths = np.linalg.norm(cell, axis=1)

    A = cell / lengths[:, None]

    ox = np.arange(0, lengths[0] - 1.0e-3, real_step[0])
    oy = np.arange(0, lengths[1] - 1.0e-3, real_step[1])
    oz = np.arange(0, lengths[2] - 1.0e-3, real_step[2])

    u, v = u / np.linalg.norm(u), v / np.linalg.norm(v)

    n = np.cross(u, v)
    n /= np.linalg.norm(n)

    u_perp = np.cross(n, u)
    u_perp /= np.linalg.norm(u_perp)

    # The basis of the plane
    B = np.array([u, u_perp, n])
    Bo = np.dot(B, o)

    zoff = ((0 - o[1]) * (u[0] * v[2] - v[0] * u[2]) -
            (0 - o[0]) * (u[1] * v[2] - v[1] * u[2])) \
        / (u[0] * v[1] - v[0] * u[1]) + o[2]
    zoff = np.dot(B, [0, 0, zoff])[-1]

    x, y = np.arange(*size_u, step), np.arange(*size_v, step)
    x += Bo[0]
    y += Bo[1]

    X, Y = np.meshgrid(x, y)

    Bvectors = np.stack((X, Y)).reshape(2, -1).T
    Bvectors = np.hstack((Bvectors, np.ones((Bvectors.shape[0], 1)) * zoff))

    vectors = np.dot(Bvectors, np.linalg.inv(B).T)
    # If the cell is not orthogonal, we need to rotate the vectors
    vectors = np.dot(vectors, np.linalg.inv(A))

    D = interpn((ox, oy, oz),
                cube['data'],
                vectors,
                bounds_error=False,
                method='linear'
                ).reshape(X.shape)

    return X - Bo[0], Y - Bo[1], D
