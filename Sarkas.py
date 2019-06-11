#############################################################################################
#                       Sarkas                                                              #
#                                                                                           #
# A code that executes molecular dynamics simulation for a Yukawa plasma                    #
# using the efficient Particle-Particle-Particle-Mesh algorithm for force computation.      #
# The code constitutes a number of functions that are in separate files.                    #
#                                                                                           #
# Developed by the research group of:                                                       #
#  Professor Michael S. Murillo                                                             #
#  murillom@msu.edu                                                                         #
# Dept. of Computational Mathematics, Science, and Engineering,                             #
# Michigan State University                                                                 #
#############################################################################################

# python modules
from mpi4py import MPI
import numpy as np
import numba as nb
import time
import sys

t1 = time.time()

# Importing MD modules
import S_read as read
import S_initialize_pos_vel as initialize_pos_vel
import S_velocity_verlet as velocity_verlet
import S_thermostat as thermostat
import S_yukawa_gf_opt as yukawa_gf_opt
import S_EGS as EGS
import S_p3m as p3m
import S_read_input as read_input
import S_global_names as glb
import S_constants as const

def prime_factors(n):
    i = 2
    factors = []
    while i * i <= n:
        if n % i:
            i += 1
        else:
            n //= i
            factors.append(i)
    if n > 1:
        factors.append(n)
    return factors

def domain_decomp(n):
    pf= prime_factors(n)
    Ln = len(pf)
    rtn = np.array([1,1,1])
    if Ln == 1:
        rtn = np.array([pf[0],1,1])
    elif Ln == 2:
        rtn = np.array([pf[0],pf[1],1])
    else:
        a = pf.pop(-1)
        b = pf.pop(-1)
        c = pf.pop(-1)
        rtn = np.array([c,b,a])
        while pf:
            fact = pf.pop(-1)
            rtn[np.argmin(rtn)] *= fact
    return rtn

comm = MPI.COMM_WORLD

global size
global rank
global DEBUG
DEBUG = True
size = comm.size
rank = comm.rank

input_file = sys.argv[1]
# Reading MD conditions from input file
read_input.parameters(input_file)

#glb.Zi = 1

Zi = glb.Zi
q1 = glb.q1
q2 = glb.q2
ni = glb.ni
wp = glb.wp
ai = glb.ai
mi= const.pMass

# Other MD parameters
if(glb.potential_type == glb.Yukawa_PP or glb.potential_type == glb.Yukawa_P3M):
    if(glb.units == "Yukawa"):
        glb.T_desired = 1/(glb.Gamma)                # desired temperature

    if(glb.units == "cgs"):
        glb.T_desired = q1*q2/ai/(const.kb*glb.Gamma)                # desired temperature

    if(glb.units == "mks"):
        glb.T_desired = q1*q2/ai/(const.kb*glb.Gamma*4*np.pi*const.eps_0)                # desired temperature

T_desired = glb.T_desired
Nt = glb.Nt
Neq = glb.Neq
L = ai*(4.0*np.pi*glb.N/3.0)**(1.0/3.0)      # box length
glb.Lx = L
glb.Ly = L
glb.Lz = L
glb.Lv = np.array([L, L, L])              # box length vectorimport numba as nb
glb.d = np.count_nonzero(glb.Lv)              # no. of dimensions
glb.Lmax_v = np.array([L, L, L])
glb.Lmin_v = np.array([0.0, 0.0, 0.0])

#Ewald parameters
glb.G = 0.46/ai
glb.G_ew = glb.G
glb.rc *= ai

#P3M parameters
glb.Mx = 64
glb.My = 64
glb.Mz = 64
glb.hx = glb.Lx/glb.Mx
glb.hy = glb.Ly/glb.My
glb.hz = glb.Lz/glb.Mz
glb.p = 6
glb.mx_max = 3
glb.my_max = 3
glb.mz_max = 3

t2 = time.time()

G_k=0
kx_v=0
ky_v=0
kz_v=0
A_pm=0
if( p3m == 1):
    G_k, kx_v, ky_v, kz_v, A_pm = yukawa_gf_opt.gf_opt()
if(glb.potential_type == glb.EGS):
  EGS.init_parameters()

t3 = time.time()
glb.kappa /=glb.ai

# pre-factors as a result of using 'reduced' units
glb.af = 1.0/3.0                          # acceleration factor for Yukawa units
glb.uf = 1.0                              # potential energy factor for Yukawa units
glb.kf = 1.5                              # kinetic energy factor for Yukawa units
af = glb.af
uf = glb.uf
kf = glb.kf

N = glb.N
dt = glb.dt
glb.p3m_flag = 1 # default is P3M OFF
if(glb.pot_calc_algrthm == "PP"):
  glb.p3m_flag = 0

if(glb.verbose):
    print('\n\n----------- Molecular Dynamics Simulation of Yukawa System ----------------------')
    print("units: ", glb.units)
    if(glb.potential_type == glb.Yukawa_PP or glb.potential_type == glb.Yukawa_P3M):
      print('Gamma = ', glb.Gamma)
      print('kappa = ', glb.kappa)
      print('grid_size * Ewald_parameter (h * alpha) = ', glb.hx*glb.G_ew)
    print('Temperature = ', T_desired)
    print('No. of particles = ', glb.N)
    print('Box length along x axis = ', glb.Lv[0])
    print('Box length along y axis = ', glb.Lv[1])
    print('Box length along z axis = ', glb.Lv[2])
    print('No. of non-zero box dimensions = ', glb.d)
    print('time step = ',glb.dt)
    print('No. of equilibration steps = ', glb.Neq)
    print('No. of post-equilibration steps = ', glb.Nt)
    print('snapshot interval = ', glb.snap_int)
    print('Periodic boundary condition{1=yes, 0=no} =', glb.PBC)
    print("Langevin model = ", glb.Langevin_model)
    if(glb.units != "Yukawa"):
        print("plasma frequency, wi = ", glb.wp)
        print("number density, ni = ", glb.ni)
# Particle positions and velocities array

# DECOMPOSE DOMAIN ####################

Nlocal = int(N/size)

if rank < (N%size):
    Nlocal += 1
if DEBUG:
    print("rank: %d, N = %d" %(rank,Nlocal))
    print("prime_factors(3*3*5*7) = ", prime_factors(3*3*5*7) )
    print( "domain_decomp(3*3*5*7) = ",domain_decomp(3*3*5*7) )

decomp = domain_decomp(3*3*5*7)

Lxlocal = L/decomp[0]
Lylocal = L/decomp[1]
Lzlocal = L/decomp[2]

LxMin = (rank%decomp[0])*Lxlocal
LxMax = Lxlocal + LxMin

LyMin = np.floor(rank/decomp[1])*Lylocal
LyMax = LyMin + Lylocal

LzMin = np.floor(rank/(decomp[0]*decomp[1]))*Lzlocal
LzMax = LzMin + Lzlocal

if DEBUG:
    print("LxMin = ", LxMin)
    print("LxMax = ", LxMax)
    print("rank mod decomp[0] = ",(rank%decomp[0]))
    print("LyMin = ", LyMin)
    print("LyMax = ", LyMax)
    print("rank mod decomp[1] = ",(rank%decomp[1]))
    print("LzMin = ", LzMin)
    print("LzMax = ", LzMax)
    print("rank mod decomp[2] = ",(rank%decomp[2]))

pos = np.zeros((Nlocal, glb.d))
vel = np.zeros_like(pos)
acc = np.zeros_like(pos)
Z = np.ones(N)

acc_s_r = np.zeros_like(pos)
acc_fft = np.zeros_like(pos)

rho_r = np.zeros((glb.Mz, glb.My, glb.Mx))
E_x_p = np.zeros(glb.N)
E_y_p = np.zeros(glb.N)
E_z_p = np.zeros(glb.N)

#####################################


# F(k,t): Spatial Fourier transform of density fluctutations
dq = 2.*np.pi/L
if(glb.verbose):
    print('smallest interval in Fourier space for S(q,w): dq = ', dq)

q_max = 30/ai
glb.Nq = 3*int(q_max/dq)
Nq = glb.Nq   # 3 is for x, y, and z commponent

#n_q_t = np.zeros((Nt, Nq, 3),dtype='complex128') #

# initializing the q vector
qv = np.zeros(Nq)

for iqv in range(0, Nq, 3):
    iq = iqv/3.
    qv[iqv] = (iq+1.)*dq
    qv[iqv+1] = (iq+1.)*np.sqrt(2.)*dq
    qv[iqv+2] = (iq+1.)*np.sqrt(3.)*dq

#array for temperature, total energy, kinetic energy, potential energy
t_Tp_E_K_U2 = np.zeros((1,5))

# Initializing particle positions and velocities
if glb.init == 1:
    
    print('\nReading initial particle positions and velocities from file...')
    f_input = 'init.out'           # name of input file
    pos, vel = read.initL(pos, vel, f_input)
    
else:
    
    print('\nAssigning random initial positions and velocities...')
    
    # initial particle positions uniformly distributed in the box
    # initial particle velocities with Maxwell-Boltzmann distribution
    pos, vel = initialize_pos_vel.initial(pos, vel, T_desired,Nlocal)

t4 = time.time()
# Calculating initial forces and potential energy
U, acc = p3m.force_pot(pos, acc, Z, G_k, kx_v, ky_v, kz_v, acc_s_r, acc_fft, rho_r, E_x_p, E_y_p, E_z_p)

K = 0.5*mi*np.ndarray.sum(vel**2)
Tp = (2/3)*K/float(N)/const.kb
if(glb.units == "Yukawa"):
    K *= 3
    Tp *= 3
E = K + U
print("=====T, E, K, U = ", Tp, E, K, U)

print('\n------------- Equilibration -------------')
#print('time - temperature')
for it in range(Neq):
#    print("it = ", it)
    pos, vel, acc, U = thermostat.vscale(pos, vel, acc, T_desired, it, Z, G_k, kx_v, ky_v, kz_v, acc_s_r, acc_fft, rho_r, E_x_p, E_y_p, E_z_p)
#---------------
    K = 0.5*mi*np.ndarray.sum(vel**2)
    Tp = (2/3)*K/float(N)/const.kb
    if(glb.units == "Yukawa"):
        K *= 3
        Tp *= 3

    E = K + U
    if(it%glb.snap_int == 0 and glb.verbose):
        print("Equilibration: timestep, T, E, K, U = ", it, Tp, E, K, U)
t5 = time.time()

print('\n------------- Production -------------')
# Opening files for writing particle positions, velcoities and forces
f_output = open('p_v_a.out','w')
f_output_E = open('t_T_totalE_kinE_potE.out','w')
f_xyz = open('p_v_a.xyz','w')

#print('time - total energy - kinetic energy - potential energy')

for it in range(Nt):
    
    pos, vel, acc, U = velocity_verlet.update_Langevin(pos, vel, acc, Z, G_k, kx_v, ky_v, kz_v, acc_s_r, acc_fft, rho_r, E_x_p, E_y_p, E_z_p,Nlocal)

    #K = 0.5*mi*np.ndarray.sum(vel**2)
    #Tp = (2/3)*K/float(N)/const.kb
    #if(glb.units == "Yukawa"):
    #    K *= 3.
    #    Tp *= 3.

    #E = K + U

    #if(it%glb.snap_int == 0 and glb.verbose):
    #    print("productoin: timestep, T, E, K, U = ", it, Tp, E, K, U)
    
    #t_Tp_E_K_U = np.array([dt*it, Tp, E, K, U])
    #t_Tp_E_K_U2[:] = t_Tp_E_K_U
    
    # Spatial Fourier transform
    #for iqv in range(Nq):
    #    q_p = qv[iqv]
    #    n_q_t[it,iqv,0] = np.sum(np.exp(-1j*q_p*pos[:,0]))
    #    n_q_t[it,iqv,1] = np.sum(np.exp(-1j*q_p*pos[:,1]))
    #    n_q_t[it,iqv,2] = np.sum(np.exp(-1j*q_p*pos[:,2]))
    
    # writing particle positions and velocities to file
    #if glb.write_output == 1:
    #    if np.mod(it+1, glb.snap_int) == 0:
    #        irp = np.hstack((pos, vel, acc))
    #        np.savetxt(f_output, irp)
    #        np.savetxt(f_output_E, t_Tp_E_K_U2)
    #        
    #        if glb.write_xyz == 1:
    #            f_xyz.writelines('{0:d}\n'.format(N))
    #            f_xyz.writelines('x y z vx vy vz ax ay az\n')
    #            np.savetxt(f_xyz,irp)

#np.save('n_qt',n_q_t)

# closing output files        
f_output.close()
f_output_E.close()
f_xyz.close()
# saving last positions, velocities and accelerations
irp2 = np.hstack((pos,vel,acc))
np.savetxt('p_v_a_final.out',irp2)

t6 = time.time()

if(glb.verbose):
    print('Time for importing required libraries = ', t2-t1)
    print('Time for computing converged Greens function = ', t3-t2)
    print('Time for initialization = ', t4-t3)
    print('Time for equilibration = ', t5-t4)
    print('Time for production = ', t6-t5)
    print('Total elapsed time = ', t6-t1)

# end of the code
