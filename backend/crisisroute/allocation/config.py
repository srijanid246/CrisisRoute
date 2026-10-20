from dataclasses import dataclass


@dataclass
class GAConfig:
    population_size: int = 80
    generations: int = 150
    crossover_rate: float = 0.8
    mutation_rate: float = 0.05
    elitism_count: int = 2
    tournament_size: int = 3
    seed: int = 42
