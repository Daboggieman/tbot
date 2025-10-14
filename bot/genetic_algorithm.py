import random
import numpy as np
from deap import base, creator, tools, algorithms
from backtesting_engine import BacktestingEngine
from strategies import MovingAverageCrossoverStrategy
import logging

logger = logging.getLogger(__name__)

class GeneticStrategyDiscovery:
    def __init__(self, data, population_size=50, generations=10):
        self.data = data
        self.population_size = population_size
        self.generations = generations

        # Define the individual (strategy parameters)
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMax)

        self.toolbox = base.Toolbox()
        # Attributes: short_window, long_window
        self.toolbox.register("attr_short", random.randint, 5, 50)
        self.toolbox.register("attr_long", random.randint, 20, 100)
        self.toolbox.register("individual", tools.initCycle, creator.Individual,
                             (self.toolbox.attr_short, self.toolbox.attr_long), n=1)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)

        self.toolbox.register("evaluate", self.evaluate_strategy)
        self.toolbox.register("mate", tools.cxTwoPoint)
        self.toolbox.register("mutate", tools.mutUniformInt, low=[5, 20], up=[50, 100], indpb=0.2)
        self.toolbox.register("select", tools.selTournament, tournsize=3)

    def evaluate_strategy(self, individual):
        """Fitness function: backtest the strategy and return Sharpe ratio."""
        short_window, long_window = individual
        if short_window >= long_window:
            return -999,  # Invalid, penalize

        strategy = MovingAverageCrossoverStrategy(short_window=short_window, long_window=long_window)
        engine = BacktestingEngine(strategy, self.data)
        try:
            engine.run_backtest()
            sharpe = engine.sharpe_ratio
            return sharpe,
        except Exception as e:
            logger.error(f"Backtest failed for {individual}: {e}")
            return -999,

    def discover(self):
        """Run the genetic algorithm to discover new strategies."""
        pop = self.toolbox.population(n=self.population_size)
        hof = tools.HallOfFame(1)
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)
        stats.register("std", np.std)
        stats.register("min", np.min)
        stats.register("max", np.max)

        algorithms.eaSimple(pop, self.toolbox, cxpb=0.5, mutpb=0.2, ngen=self.generations,
                            stats=stats, halloffame=hof, verbose=True)

        best_individual = hof[0]
        best_fitness = best_individual.fitness.values[0]
        logger.info(f"Best strategy found: {best_individual}, Fitness: {best_fitness}")

        return best_individual, best_fitness
