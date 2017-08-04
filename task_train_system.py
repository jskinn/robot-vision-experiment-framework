import sys
import logging
import logging.config
import traceback
import bson.objectid

import config.global_configuration as global_conf
import database.client
import util.database_helpers as dh


def main(*args):
    """
    Train a trainee with a trainer.
    This represents a basic task.
    Scripts to run this will be autogenerated by the job system
    The first argument is the trainer ID, the second
    :return: void
    """
    if len(args) >= 2:
        trainer_id = bson.objectid.ObjectId(args[0])
        trainee_id = bson.objectid.ObjectId(args[1])
        experiment_id = bson.objectid.ObjectId(args[2]) if len(args) >= 3 else None

        config = global_conf.load_global_config('config.yml')
        logging.config.dictConfig(config['logging'])
        log = logging.getLogger(__name__)
        db_client = database.client.DatabaseClient(config=config)

        trainer = dh.load_object(db_client, db_client.trainer_collection, trainer_id)
        trainee = dh.load_object(db_client, db_client.trainee_collection, trainee_id)
        experiment = dh.load_object(db_client, db_client.experiments_collection, experiment_id)

        log.info("Start training trainee {0} ({1}) with trainer {2} (3)".format(
            trainee_id,
            trainee.__module__ + '.' + trainee.__class__.__name__,
            trainer_id,
            trainer.__module__ + '.' + trainer.__class__.__name__
        ))
        success = False
        retry = True
        if trainer is not None and trainee is not None:
            if not trainer.can_train_trainee(trainee):
                retry = False
            else:
                try:
                    system = trainer.train_vision_system(trainee)
                except Exception:
                    system = None
                    log.error("Error occurred while trainer {0} trains trainee {1}:\n{2}".format(
                        trainer_id,
                        trainee_id,
                        traceback.format_exc()
                    ))
                if system is not None:
                    system_id = db_client.system_collection.insert(system.serialize())
                    if experiment is not None:
                        log.info("Successfully trained system {0}, adding to experiment {1}".format(system_id,
                                                                                                    experiment_id))
                        experiment.add_system(trainer_id=trainer_id, trainee_id=trainee_id,
                                              system_id=system_id, db_client=db_client)
                        success = True
        if not success and experiment is not None:
            if retry:
                log.warning("Failed to train trainee {0} with trainer {1}, retrying.".format(trainee_id, trainer_id))
                experiment.retry_training(trainer_id=trainer_id, trainee_id=trainee_id, db_client=db_client)
            else:
                log.info("Trainee {0} is incompatible with trainer {1}.".format(trainee_id, trainer_id))
                experiment.mark_training_unsupported(trainer_id=trainer_id, trainee_id=trainee_id, db_client=db_client)


if __name__ == '__main__':
    main(*sys.argv[1:])
