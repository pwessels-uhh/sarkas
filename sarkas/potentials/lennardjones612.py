"""
Module for handling Lennard-Jones interaction
"""

import numpy as np
import numba as nb
import yaml


def setup(params, read_input=True):
    """
    Updates ``params`` class with LJ potential parameters.

    Parameters
    ----------
    read_input: bool
        Flag to read inputs from YAML input file.

    params : object
        Simulation's parameters

    """

    if read_input:
        with open(params.input_file, 'r') as stream:
            dics = yaml.load(stream, Loader=yaml.FullLoader)

            for lkey in dics:
                if lkey == "Potential":
                    for keyword in dics[lkey]:
                        for key, value in keyword.items():
                            if key == "rc":  # cutoff
                                params.Potential.rc = float(value)

                            if key == "epsilon":
                                params.Potential.lj_eps = np.array(value)

                            if key == "sigma":
                                params.Potential.lj_sigma = np.array(value)

    update_params(params)


def update_params(params):
    """
    Create potential dependent simulation's parameters.

    Parameters
    ----------
    params : object
        Simulation's parameters

    """
    if not params.BC.open_axes:
        params.Potential.LL_on = True  # linked list on
        if not hasattr(params.Potential, "rc"):
            print("\nWARNING: The cut-off radius is not defined. L/2 = ", params.Lv.min() / 2, "will be used as rc")
            params.Potential.rc = params.Lv.min() / 2.
            params.Potential.LL_on = False  # linked list off

        if params.Potential.method == "PP" and params.Potential.rc > params.Lv.min() / 2.:
            print("\nWARNING: The cut-off radius is > L/2. L/2 = ", params.Lv.min() / 2, "will be used as rc")
            params.Potential.rc = params.Lv.min() / 2.
            params.Potential.LL_on = False  # linked list off

    LJ_matrix = np.zeros((2, params.num_species, params.num_species))

    for j in range(params.num_species):
        for i in range(params.num_species):
            idx = i * params.num_species + j
            LJ_matrix[0, i, j] = params.Potential.lj_eps[idx]
            LJ_matrix[1, i, j] = params.Potential.lj_sigma[idx]

    params.Potential.matrix = LJ_matrix
    params.force = LJ_force_PP

    # Calculate the (total) plasma frequency
    wp_tot_sq = 0.0
    sigma2 = 0.0
    epsilon_tot = 0.0
    for i in range(params.num_species):
        params.species[i].epsilon = params.Potential.lj_eps[i]
        params.species[i].sigma = params.Potential.lj_sigma[i]

        wp2 = 48.0 * params.species[i].epsilon / params.species[i].sigma ** 2
        params.species[i].wp = np.sqrt(wp2)
        sigma2 += params.species[i].sigma
        epsilon_tot += params.species[i].epsilon
        wp_tot_sq += wp2

    params.wp = np.sqrt(wp_tot_sq)

    params.PP_err = np.sqrt(np.pi * sigma2 ** 12 / (13.0 * params.Potential.rc ** 13))
    params.PP_err *= np.sqrt(params.N / params.box_volume) * params.aws ** 2
    params.Potential.Gamma_eff = epsilon_tot/(params.kB*params.T_desired)


@nb.njit
def LJ_force_PP(r, pot_matrix_ij):
    """
    Calculates the PP force between particles using Lennard-Jones Potential.
    
    Parameters
    ----------
    pot_matrix_ij : array
        LJ potential parameters. 

    r : float
        Particles' distance.


    Returns
    -------
    U : float
        Potential.

    force : float
        Force.
    """
    """
    Notes
    -----
    pot_matrix[0] = epsilon
    pot_matrix[1] = sigma
    """

    epsilon = pot_matrix_ij[0]
    sigma = pot_matrix_ij[1]
    s_over_r = sigma / r
    s_over_r_6 = s_over_r ** 6
    s_over_r_12 = s_over_r ** 12

    U = 4.0 * epsilon * (s_over_r_12 - s_over_r_6)
    force = 48.0 * epsilon * (s_over_r_12 - 0.5 * s_over_r_6) / r ** 2

    return U, force
