import math

import config
from core.physics import normalize_angle
from brain.profiles import PROFILES

class Creature:
    def __init__(self, x, y, angle, energy, brain, profile, uid=0, parent_id=None, birth_tick=0, lineage_gen=0,
                 size=1.0):
        self.x = float(x)
        self.y = float(y)
        self.angle = angle
        self.speed = 0.0  # Current speed, decided by the network at each tick
        self.energy = energy
        self.brain = brain
        self.profile = profile   # Name of its network profile (species), see brain/profiles.py
        self._spec = PROFILES[profile]
        self.alive = True
        self.set_size(size)
        self.death_cause = None   # "faim" or "vieillesse" (poison kills through hunger)
        # Lineage (continuous evolution): identity, parent, birth, depth of the lineage (0 = random founder)
        self.uid = uid
        self.parent_id = parent_id
        self.birth_tick = birth_tick
        self.lineage_gen = lineage_gen
        self.last_birth_age = None   # Age at its last birth (cooldown)
        self.children = 0
        self.food_eaten = 0 
        self.poison_hits = 0
        self.obstacle_ticks = 0   # Ticks spent pressed against an obstacle
        self.touching = False     # Pressed against an obstacle at the last tick (a sensor of some profiles)
        self.memory = [0.0] * PROFILES[profile]["memory"]   # Extra network outputs, fed back as inputs at the next tick
        self.age = 0
        # Exploration metrics: what the creature does when it sees no food
        self.food_nearby = True  # Set by World.sense each tick
        self.blind_ticks = 0
        self.blind_speed_sum = 0.0
        self.blind_turn_sum = 0.0
        self.last_turn = 0.0     # Turn output of the last tick (exploration measures)
        self.unseen_ticks = 0    # Ticks since it last saw an available food (sensor «faim»)
        self.speed_sum = 0.0     # Sum of its speed over its life: mean speed = speed_sum / age

    def set_size(self, size):
        """Body gene. `body` is the size that acts (1 unless SIZE_MODE is "actif"); everything the body changes is
        computed here once: contact radius, energy reserve, base and moving costs."""
        self.size = size
        self.body = size if config.SIZE_MODE == "actif" else 1.0
        self.radius = config.CREATURE_RADIUS * self.body
        self.energy_max = config.ENERGY_MAX * self.body
        self.base_cost = config.ENERGY_BASE_COST * self.body ** config.SIZE_BASE_EXPONENT
        self.move_cost = config.ENERGY_MOVE_COST * self.body

    def update(self, inputs, world_width, world_height):
        if not self.alive:
            return
        if self.energy <= 0:
            self.alive = False
            self.death_cause = "faim"
            return

        # The network decides: outputs are in [-1, 1] (tanh)
        outputs = self.brain.forward(inputs)
        turn = float(outputs[0])
        if self._spec["speed_output"]:
            speed_command = float(outputs[1])
            first_memory = 2
        else:
            speed_command = self._spec["fixed_speed"]   # This species cannot change its speed
            first_memory = 1
        if len(outputs) > first_memory:
            self.memory = [float(v) for v in outputs[first_memory:]]

        # Inertia: the network asks for a target speed, the speed moves toward it with limited acceleration
        target_speed = (speed_command + 1.0) / 2.0 * config.CREATURE_MAX_SPEED
        change = max(-config.CREATURE_ACCELERATION, min(config.CREATURE_ACCELERATION, target_speed - self.speed))
        self.speed += change

        # The faster the creature goes, the less it can turn
        max_turn = config.CREATURE_MAX_TURN * (1.0 - config.TURN_SPEED_PENALTY * self.speed / config.CREATURE_MAX_SPEED)
        self.angle = normalize_angle(self.angle + turn * max_turn)

        # Blind = no available food in view (food that was eaten is somewhere else when it comes back)
        self.last_turn = turn
        if not self.food_nearby:
            self.blind_ticks += 1
            self.blind_speed_sum += self.speed
            self.blind_turn_sum += abs(turn)
            self.unseen_ticks += 1
        else:
            self.unseen_ticks = 0

        # Update the creature's position based on its speed and angle
        self.x += self.speed * math.cos(self.angle)
        self.y += self.speed * math.sin(self.angle)

        # Keep the creature within the bounds of the world
        self.x  %= world_width
        self.y  %= world_height

        # Moving costs energy: base cost + cost proportional to speed
        self.energy -= self.base_cost + self.move_cost * self.speed

        self.age += 1 #Added age increment to track how long the creature has been alive
        self.speed_sum += self.speed

    def hit_by_poison(self, amount):
        """Touching a poison costs energy. The creature dies at its next update if the energy reaches 0."""
        if not self.alive:
            return
        self.energy -= amount
        self.poison_hits += 1

    def eat_food(self,amount):
        if not self.alive:
            return
        self.energy = min(self.energy + amount, self.energy_max)  # The excess is lost
        self.food_eaten += 1
        
