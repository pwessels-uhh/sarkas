'''
S_params.py

a code to read Sarkas input file with a YAML format.

species - species to use in the simulation
    name: species name
    mass: species mass
    charge: species charge
    Temperature: desired species temperature

load - particles loading described in Species
    species_name: should be one of names in Species
    Num: number of particles of the species to load
    number_density: number density of the species

potential - Two body potential 
    type: potential type. Yukawa, EGS are available
    Gamma: plasma prameter Gamma
    kappa: plasma parameter kappa

thermostat - Thermostat to equilibrize the system
    type: Thermostat type. Only Berendsen for now.

Langevin
    type: Langevin model type. Only BBK for now.

control - general setup values for the simulations
    dt: timestep
    Neq: number of steps to make the system equblizing
    Nstep: number of steps for data collecting
    BC: Boundary condition. periodic only
    units: cgs, mks, Yukawa
    dump_step: output step
    seed: random number seed for particles' positions and velocities
    restart: restart the simulation from this step. Not yet implemented.
'''

import yaml

class Params:
    def __init__(self):
        self.species = [] 
        self.potential = [] 
        self.load = []
        self.Langevin = []
        self.thermostat = []
        self.control = []

    class species_spec:
        def __init__(self):
            self.name = None
            self.mass = None
            self.charge = None
            self.T0 = None

    class species_load:
        def __init__(self):
            self.species_name = None
            self.Num = None
            self.np = None

    class plasma_potential:
        def __init__(self):
            self.type = None
            self.Gamma = None
            self.kappa = None

    class md_thermostat:
        def __init__(self):
            self.type = None

    class md_Langevin:
        def __init__(self):
            self.type = None
            self.gamma = None

    class md_control:
        def __init__(self):
            self.dt = None
            self.Neq = None
            self.Nstep = None
            self.BC = None
            self.units= None
            self.dump_step = None
            self.seed = None
            self.restart = None 

    def setup(self, filename):
        with open(filename, 'r') as stream:
            dics = yaml.load(stream)

            for keyword in dics['Region']:
                for key, value in keyword.items():
                    if(key == 'Species'):
                        spec = self.species_spec()
                        self.species.append(spec)
                        ic = len(self.species) - 1

                        for key, value in value.items():
                            if(key == 'name'):
                                self.species[ic].name = value

                            if(key == 'mass'):
                                self.species[ic].mass = value

                            if(key == 'charge'):
                                self.species[ic].charge = value

                            if(key == 'Temperature'):
                                self.species[ic].T0 = value

                    if(key == 'Load'):
                        load = self.species_load()
                        self.load.append(load)
                        ic = len(self.load) - 1

                        for key, value in value.items():
                            if(key == 'species_name'):
                                self.load[ic].species_name = value

                            if(key == 'Num'):
                                self.load[ic].Num = int(value)

                            if(key == 'number_density'):
                                self.load[ic].np = value
   
                    if(key == 'Potential'):
                        plasma_potential = self.plasma_potential()
                        self.potential.append(plasma_potential)
                        ic = len(self.potential) - 1
                        for key, value in value.items():
                            if(key == 'algorithm'):
                                self.potential[0].algorithm = value

                            if(key == 'type'):
                                self.potential[0].type = value

                            if(key == 'Gamma'):
                                self.potential[0].Gamma = value

                            if(key == 'kappa'):
                                self.potential[0].kappa = value

                            if(key == 'rc'):
                                self.potential[0].rc = value

                    if(key == 'Thermostat'):
                        md_thermostat = self.md_thermostat()
                        self.thermostat.append(md_thermostat)
                        ic = len(self.thermostat) - 1

                        for key, value in value.items():
                            if(key == 'type'):
                                self.thermostat[0].type = value

                    if(key == 'Langevin'):
                        md_Langevin = self.md_Langevin()
                        self.Langevin.append(md_Langevin)
                        ic = len(self.Langevin) - 1
                        for key, value in value.items():
                            if(key == 'type'):
                                self.Langevin[0].type = value
                            if(key == 'gamma'):
                                self.Langevin[0].gamma = value

                    if(key == 'Control'):
                        md_control = self.md_control()
                        self.control.append(md_control)
                        ic = len(self.control) - 1
                        for key, value in value.items():
                            if(key == 'dt'):
                                self.control[0].dt = value
    
                            if(key == 'Nstep'):
                                self.control[0].Nstep = int(value)

                            if(key == 'Neq'):
                                self.control[0].Neq = int(value)

                            if(key == 'BC'):
                                self.control[0].BC = value

                            if(key == 'units'):
                                self.control[0].units = value

                            if(key == 'dump_step'):
                                self.control[0].dump_step = value

                            if(key == 'ptcls_init'):
                                if(value == "random"):
                                    self.control[0].init = 0
                                if(value == "file"):
                                    self.control[0].init = 1

                            if(key == "writeout"):
                                if(value == False):
                                    self.control[0].writeout = 0
                                if(value == True):
                                    self.control[0].writeout = 1

                            if(key == "writexyz"):
                                if(value == False):
                                    self.control[0].writexyz = 0
                                if(value == True):
                                    self.control[0].writexyz = 1

                            if(key == 'random_seed'):
                                self.control[0].seed = int(value)

                            if(key == 'restart'):
                                self.control[0].restart = value

                            if(key == 'verbose'):
                                if(value == False):
                                    self.control[0].verbose = 0
                                if(value == True):
                                    self.control[0].verbose = 1
