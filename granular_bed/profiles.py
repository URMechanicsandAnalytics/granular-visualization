import math


class BedProfile:
    """
    For various operations/analysis on particle profiles

    For initialization, there needs to be an input 2d array that consists of the following:
        - A 2D array with dimensions of at least <number of particles> x 3 where:
            - Column 1 ( array[n][0] ): Particle x coordinate
            - Column 2 ( array[n][0] ): Particle y coordinate
            - Column 3 ( array[n][0] ): Particle radius
    """

    def __init__(self, particle_positions) -> None:

        # particle
        self.particle_positions = particle_positions
        self.num_particles = len(particle_positions)

    def p_square_count(self, current_x, current_y, side_length) -> int:
        """
        method to find the particle counts per region
        """

        # defining the region
        lower_x = current_x - side_length / 2
        upper_x = current_x + side_length / 2

        lower_y = current_y - side_length / 2
        upper_y = current_y + side_length / 2

        # reducing the region to the one
        reduced_positions = [pos for pos in self.particle_positions if (upper_y > pos[1] > lower_y)]

        # the initial count is 0 because it's looking over a specific region not a particle
        count = 0
        for position in reduced_positions:

            # counting particles that are within the box
            if upper_x > position[0] > lower_x:
                count += 1

        return count

    def p_circle_count(self, current_x, current_y, radius_multiplier) -> int:
        """
        Method to find the count the number of particles in a region"""
        count = 1

        for params in self.particle_positions:

            if params[0] == current_x and params[1] == current_y:
                continue
            if math.dist((current_x, current_y), (params[0], params[1])) < radius_multiplier * params[2]:
                count += 1

        return count

    def p_nearest(self, particle_x, particle_y) -> float:
        """
        method to find the distance to the nearest particle"""

        # importing the dist() function

        # for a scale distance, the maximum possible distance between 2 particles.
        MAX_DIST = 1
        distance = MAX_DIST

        for pos in self.particle_positions:

            # stopping the minimum distance from being zero
            if pos[0] == particle_x and pos[1] == particle_y:
                continue

            if math.dist((pos[0], pos[1]), (particle_x, particle_y)) < distance:
                distance = math.dist((pos[0], pos[1]), (particle_x, particle_y))

        # print(distance)
        return distance

    def p_count_near_particle(self, particle_x, particle_y, radius_multiplier) -> int:
        """
        Method to count the number of particles near a given particle
        given a particle's position and a valid radius nearby
        
            - the radius_multiplier argument is the scale factor that multiplies the radius of the particle
            - doesn't count itself as a particle
        """

        # scale factor for radius
        R_SCALEFACTOR = radius_multiplier

        # looping through each particle
        count = 1  # counting itself as 1 particle
        for params in self.particle_positions:

            # the distance within which to count
            distance = params[2] * R_SCALEFACTOR

            # ignoring itself as a count
            if params[0] == particle_x and params[1] == particle_y:
                continue

            # counting if the particle is within the region
            if math.dist((params[0], params[1]), (particle_x, particle_y)) < distance:
                count += 1

        # if there are 2 or less particles (including itself) in the area, it's just set to 1
        if count < 3:
            return 1

        return count

    def p_is_surface(self, particle_x, particle_y) -> int:
        """
        method that tells whether or not a particle is a surface particle
            - (returns 1 if there are less than 2 particles above a given particle)"""

        above_particles_count = 0
        for params in self.particle_positions:

            # ignoring anything below
            if params[1] < particle_y:
                continue

            # counting the particle if it's x is within the diameter
            if particle_x - params[2] < params[0] < particle_x + params[2]:
                above_particles_count += 1

            # if there are 2 or more particles above, it's not a surface particle.
            if above_particles_count > 1:
                return 0

        return 1
