import random
import logging
import pandas as pd
import numpy as np

from backtesting_engine import BacktestingEngine
from historical_data_manager import HistoricalDataManager
from technical_indicators import add_all_indicators

# --- Chromosome Configuration ---
INDICATORS = [
    {'name': 'SMA_10', 'type': 'line'},
    {'name': 'SMA_50', 'type': 'line'},
    {'name': 'EMA_12', 'type': 'line'},
    {'name': 'EMA_26', 'type': 'line'},
    {'name': 'RSI', 'type': 'oscillator', 'min': 20, 'max': 80},
    {'name': 'MACD', 'type': 'line'},
    {'name': 'MACD_signal', 'type': 'line'},
]
PRICE_INDICATORS = [{'name': 'Close', 'type': 'line'}]

OPERATORS = {
    'line': ['crosses_above', 'crosses_below', '>', '<'],
    'oscillator': ['>', '<']
}

# --- Dynamic Strategy for Backtesting ---
class GeneticStrategy:
    def __init__(self, chromosome):
        self.chromosome = chromosome

    def generate_signals(self, data):
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0

        all_indicator_names = [ind['name'] for ind in INDICATORS] + [ind['name'] for ind in PRICE_INDICATORS]
        for name in all_indicator_names:
            if name in data.columns:
                data[f"prev_{name}"] = data[name].shift(1)
        
        data = data.dropna()
        
        in_position = False
        entry_bar = 0
        exit_bars = self.chromosome['exit_bars']

        for i in range(len(data)):
            # Exit signal
            if in_position and (i - entry_bar) >= exit_bars:
                signals.loc[data.index[i], 'signal'] = 0 # Signal to be flat
                in_position = False
            
            # Entry signal
            if not in_position and self._check_rule(self.chromosome['rule1'], data.iloc[i]):
                signals.loc[data.index[i], 'signal'] = 1 # Signal to be long
                in_position = True
                entry_bar = i
            # If in position, keep the signal as 1
            elif in_position:
                signals.loc[data.index[i], 'signal'] = 1

        return signals

    def _check_rule(self, rule, data_slice):
        indicator1_name = rule['indicator1']
        operator = rule['operator']
        val1 = data_slice[indicator1_name]

        if 'crosses' in operator:
            indicator2_name = rule['indicator2']
            val2 = data_slice[indicator2_name]
            prev_val1 = data_slice[f"prev_{indicator1_name}"]
            prev_val2 = data_slice[f"prev_{indicator2_name}"]
            
            if operator == 'crosses_above':
                return prev_val1 <= prev_val2 and val1 > val2
            elif operator == 'crosses_below':
                return prev_val1 >= prev_val2 and val1 < val2
        else: # >, <
            if rule['indicator2']:
                val2 = data_slice[rule['indicator2']] * rule['value']
                if operator == '>':
                    return val1 > val2
                elif operator == '<':
                    return val1 < val2
            else:
                value = rule['value']
                if operator == '>':
                    return val1 > value
                elif operator == '<':
                    return val1 < value
        return False

# --- Genetic Algorithm ---
class GeneticAlgorithm:
    def __init__(self, population_size, mutation_rate, crossover_rate, generations, symbol, timeframe, start_date, end_date):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.generations = generations
        self.symbol = symbol
        self.timeframe = timeframe
        self.start_date = start_date
        self.end_date = end_date
        self.population = []
        self.data_manager = HistoricalDataManager()
        self.historical_data = self._load_data()

    def _load_data(self):
        logging.info("Loading historical data for GA...")
        data = self.data_manager.load_data_from_csv(self.symbol, self.timeframe)
        if data is None:
            logging.error("Could not load historical data. Aborting GA.")
            return None
        
        data = data.loc[self.start_date:self.end_date]

        data = add_all_indicators(data)
        logging.info(f"Data loaded and indicators added. Shape: {data.shape}")
        return data

    def _create_random_rule(self):
        rule = {}
        indicator1_meta = random.choice(INDICATORS)
        rule['indicator1'] = indicator1_meta['name']

        operator = random.choice(OPERATORS[indicator1_meta['type']])
        rule['operator'] = operator

        if 'crosses' in operator:
            possible_inds = [i for i in INDICATORS + PRICE_INDICATORS if i['type'] == 'line' and i['name'] != indicator1_meta['name']]
            indicator2_meta = random.choice(possible_inds)
            rule['indicator2'] = indicator2_meta['name']
            rule['value'] = None
        else: # >, <
            if indicator1_meta['type'] == 'oscillator':
                rule['value'] = random.randint(indicator1_meta['min'], indicator1_meta['max'])
                rule['indicator2'] = None
            else:
                 possible_inds = [i for i in INDICATORS + PRICE_INDICATORS if i['type'] == 'line' and i['name'] != indicator1_meta['name']]
                 indicator2_meta = random.choice(possible_inds)
                 rule['indicator2'] = indicator2_meta['name']
                 rule['value'] = 1 + random.uniform(-0.05, 0.05)
            
        return rule

    def _initialize_population(self):
        self.population = []
        for _ in range(self.population_size):
            chromosome = {
                'rule1': self._create_random_rule(),
                'exit_bars': random.randint(5, 100)
            }
            self.population.append(chromosome)
        logging.info(f"Initialized population with {self.population_size} chromosomes.")

    def _calculate_fitness(self, chromosome):
        if self.historical_data is None or self.historical_data.empty:
            return 0.0

        strategy = GeneticStrategy(chromosome)
        data_for_backtest = self.historical_data.copy()

        try:
            engine = BacktestingEngine(strategy, data_for_backtest)
            engine.run_backtest()
            
            sharpe = engine.sharpe_ratio
            
            if pd.isna(sharpe) or sharpe < 0:
                sharpe = 0.0
            
            if len(engine.trades) < 10:
                return 0.0

            return sharpe
        except Exception as e:
            logging.error(f"Error during fitness calculation for chromosome {chromosome}: {e}")
            return 0.0

    def _selection(self, fitness_scores):
        tournament_size = 5
        indices = list(range(len(self.population)))
        participant_indices = random.sample(indices, tournament_size)
        
        best_participant_index = -1
        best_fitness = -float('inf')
        
        for index in participant_indices:
            if fitness_scores[index] > best_fitness:
                best_fitness = fitness_scores[index]
                best_participant_index = index
                
        return self.population[best_participant_index]

    def _crossover(self, parent1, parent2):
        child = parent1.copy()
        if random.random() < 0.5:
            child['rule1'] = parent2['rule1']
        if random.random() < 0.5:
            child['exit_bars'] = parent2['exit_bars']
        return child, parent2.copy()

    def _mutation(self, chromosome):
        if random.random() < self.mutation_rate:
            if random.random() < 0.8:
                chromosome['rule1'] = self._create_random_rule()
            else:
                chromosome['exit_bars'] = random.randint(5, 100)
        return chromosome

    def run(self):
        if self.historical_data is None:
            return None

        self._initialize_population()
        
        all_time_best_chromosome = None
        all_time_best_fitness = -float('inf')

        for generation in range(self.generations):
            logging.info(f"--- Generation {generation + 1}/{self.generations} ---")

            fitness_scores = [self._calculate_fitness(chromo) for chromo in self.population]

            current_best_fitness = max(fitness_scores)
            current_best_chromosome_index = fitness_scores.index(current_best_fitness)
            current_best_chromosome = self.population[current_best_chromosome_index]
            
            if current_best_fitness > all_time_best_fitness:
                all_time_best_fitness = current_best_fitness
                all_time_best_chromosome = current_best_chromosome
                logging.info(f"New all-time best fitness: {all_time_best_fitness:.4f}")
                logging.info(f"New best strategy: {all_time_best_chromosome}")

            new_population = []
            new_population.append(all_time_best_chromosome)

            while len(new_population) < self.population_size:
                parent1 = self._selection(fitness_scores)
                parent2 = self._selection(fitness_scores)

                if random.random() < self.crossover_rate:
                    child1, child2 = self._crossover(parent1, parent2)
                else:
                    child1, child2 = parent1, parent2
                
                new_population.append(self._mutation(child1))
                if len(new_population) < self.population_size:
                    new_population.append(self._mutation(child2))

            self.population = new_population

        logging.info("Genetic Algorithm run complete.")
        logging.info(f"Best strategy found across all generations: {all_time_best_chromosome}")
        logging.info(f"Best fitness (Sharpe Ratio): {all_time_best_fitness:.4f}")
        return all_time_best_chromosome