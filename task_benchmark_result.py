import sys
import traceback
import logging
import logging.config
import bson.objectid
import config.global_configuration as global_conf
import database.client
import util.database_helpers as dh


def main(*args):
    """
    Benchmark a particular trial result with a 
    This represents a basic task.
    Scripts to run this will be autogenerated by the job system
    The first argument is the id of the trial to benchmark, and the second argument is the id of the benchmark
    :return: 
    """
    if len(args) >= 2:
        trial_id = bson.objectid.ObjectId(args[0])
        benchmark_id = bson.objectid.ObjectId(args[1])
        experiment_id = bson.objectid.ObjectId(args[2]) if len(args) >= 3 else None

        config = global_conf.load_global_config('config.yml')
        logging.config.dictConfig(config['logging'])
        log = logging.getLogger(__name__)
        db_client = database.client.DatabaseClient(config=config)

        trial_result = dh.load_object(db_client, db_client.trials_collection, trial_id)
        benchmark = dh.load_object(db_client, db_client.benchmarks_collection, benchmark_id)
        experiment = dh.load_object(db_client, db_client.experiments_collection, experiment_id)

        log.info("Benchmarking result {0} with benchmark {1}".format(trial_id, benchmark_id))
        success = False
        retry = True
        if benchmark is not None and trial_result is not None:
            if not benchmark.is_trial_appropriate(trial_result):
                retry = False
            else:
                try:
                    benchmark_result = benchmark.benchmark_results(trial_result)
                except Exception:
                    benchmark_result = None
                    log.error("Exception while benchmarking {0} with benchmark {1}:\n{2}".format(
                        trial_id, benchmark_id, traceback.format_exc()))
                if benchmark_result is not None:
                    benchmark_result_id = db_client.results_collection.insert(benchmark_result.serialize())
                    log.info("Successfully benchmarked trial {0} with benchmark {1}, producing result {2}".format(
                        trial_id, benchmark_id, benchmark_result_id))
                    if experiment is not None:
                        experiment.add_benchmark_result(trial_result_id=trial_id, benchmark_id=benchmark_id,
                                                        benchmark_result_id=benchmark_result_id, db_client=db_client)
                        success = True
        if not success and experiment is not None:
            if retry:
                experiment.retry_benchmark(trial_result_id=trial_id, benchmark_id=benchmark_id, db_client=db_client)
            else:
                experiment.mark_benchmark_unsupported(trial_result_id=trial_id, benchmark_id=benchmark_id,
                                                      db_client=db_client)


if __name__ == '__main__':
    main(*sys.argv[1:])
