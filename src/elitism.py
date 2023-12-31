from deap import tools
from deap import algorithms
import re

def eaSimpleWithElitism(population, toolbox, cxpb, mutpb, ngen, stats=None,
             halloffame=None, status_callback=None, stuck=(1e9, None), verbosity=1):
    """This algorithm is similar to DEAP eaSimple() algorithm, with the modification that
    halloffame is used to implement an elitism mechanism. The individuals contained in the
    halloffame are directly injected into the next generation and are not subject to the
    genetic operators of selection, crossover and mutation.
    """
    logbook = tools.Logbook()
    logbook.header = ['gen', 'nevals'] + (stats.fields if stats else [])

    # Evaluate the individuals with an invalid fitness
    invalid_ind = [ind for ind in population if not ind.fitness.valid]
    fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
    for ind, fit in zip(invalid_ind, fitnesses):
        ind.fitness.values = fit

    if halloffame is None:
        raise ValueError("halloffame parameter must not be empty!")

    halloffame.update(population)
    hof_size = len(halloffame.items) if halloffame.items else 0

    record = stats.compile(population) if stats else {}
    logbook.record(gen=0, nevals=len(invalid_ind), **record)
    if status_callback:
        log = re.split('[\s]+', str(logbook.stream))
        status_callback(f"gen: {log[-4]}, best: {log[-2]}, mean: {log[-1]}")

    stuck_count = 0
    last_min = False

    save_mutpb = mutpb
    radiation = 0

    # Begin the generational process
    for gen in range(1, ngen + 1):

        radiation = max(radiation - 1, 0)
        if radiation == 0:
            mutpb = save_mutpb
        else:
            stuck_count = 0
            if status_callback and gen % verbosity == 0:
                status_callback(f'gen {gen}, radiation is {radiation}')

        # Select the next generation individuals
        shock_event=''
        if stuck[0] < stuck_count:
            if stuck[1] == 'Comet Strike':
                # Generate new population for non-hof (Comet-Strike)
                if status_callback:
                    status_callback(f'gen {gen}, the comet strikes')
                offspring = toolbox.populationCreator(len(population) - 3)
                offspring.extend(halloffame.items[:3])
                halloffame.clear()
                shock_event = 'Comet Strike'
            if stuck[1] == 'Radiation Leak':
                if status_callback:
                    status_callback(f'gen {gen}, radiation leak')
                mutpb = 0.5
                radiation = stuck[0]
                shock_event='Radiation Leak'
            stuck_count = 0
        else:
            # Use defined selection algorithm
            offspring = toolbox.select(population, len(population) - hof_size)

        # Vary the pool of individuals
        offspring = algorithms.varAnd(offspring, toolbox, cxpb, mutpb)

        # Evaluate the individuals with an invalid fitness
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit

        # add the best back to population:
        offspring.extend(halloffame.items)

        # Update the hall of fame with the generated individuals
        halloffame.update(offspring)

        # Replace the current population by the offspring
        population[:] = offspring

        # Append the current generation statistics to the logbook
        record = stats.compile(population) if stats else {}
        logbook.record(gen=gen, nevals=len(invalid_ind), **record, radiation=radiation, shock_event=shock_event)
        log = re.split('[\s]+', str(logbook.stream))
        if status_callback and gen % verbosity == 0:
            status_callback(f"gen: {log[0]}, best: {log[2]}, mean: {log[3]}")

        # Check if minimum has changed vs previous iteration, else raise stuck_count
        new_min = min(logbook.select('min'))

        if last_min:
            if new_min == last_min:
                stuck_count += 1
            else:
                stuck_count = 0

        if radiation == 0:
            if status_callback and gen % verbosity == 0:
                status_callback(f'gen {gen}, stuck count is {stuck_count}')

        last_min = new_min

        # early stopping, if zero is reached (optimum)
        if last_min == 0:
            break

    return population, logbook

