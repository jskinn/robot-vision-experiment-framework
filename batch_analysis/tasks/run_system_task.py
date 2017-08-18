import batch_analysis.task


class RunSystemTask(batch_analysis.task.Task):
    """
    A task for running a system with an image source. Result will be a trial result id.
    """
    def __init__(self, system_id, image_source_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._system = system_id
        self._image_source = image_source_id

    @property
    def system(self):
        return self._system

    @property
    def image_source(self):
        return self._image_source

    def run_task(self, db_client):
        import logging
        import traceback
        import runners.trial_runner
        import util.database_helpers as dh

        system = dh.load_object(db_client, db_client.system_collection, self.system)
        image_source = dh.load_object(db_client, db_client.image_source_collection, self.image_source)

        if system is None:
            logging.getLogger(__name__).error("Could not deserialize system {0}".format(self.system))
            self.mark_job_failed()
        elif image_source is None:
            logging.getLogger(__name__).error("Could not deserialize image source {0}".format(self.image_source))
            self.mark_job_failed()
        elif not system.is_image_source_appropriate(image_source):
            logging.getLogger(__name__).error("Image source {0} is inappropriate for system {1}".format(
                self.image_source, self.system))
            self.mark_job_failed()
        else:
            logging.getLogger(__name__).info("Start running system {0} ({1}) with image source {2}".format(
                self.system,
                system.__module__ + '.' + system.__class__.__name__,
                self.image_source))
            try:
                trial_result = runners.trial_runner.run_system_with_source(system, image_source)
            except Exception:
                trial_result = None
            if trial_result is None:
                logging.getLogger(__name__).error("Error occurred while running system {0} "
                                                  "with image source {1}:\n{2}".format(
                    self.system, self.image_source, traceback.format_exc()))
                self.mark_job_failed()
            else:
                trial_result_id = db_client.trials_collection.insert(trial_result.serialize())
                logging.getLogger(__name__).info(("Successfully ran system {0} with image source {1},"
                                                  "producing trial result {2}").format(
                    self.system, self.image_source, trial_result_id))
                self.mark_job_complete(trial_result_id)

    def serialize(self):
        serialized = super().serialize()
        serialized['system_id'] = self.system
        serialized['image_source_id'] = self.image_source
        return serialized

    @classmethod
    def deserialize(cls, serialized_representation, db_client, **kwargs):
        if 'system_id' in serialized_representation:
            kwargs['system_id'] = serialized_representation['system_id']
        if 'image_source_id' in serialized_representation:
            kwargs['image_source_id'] = serialized_representation['image_source_id']
        return super().deserialize(serialized_representation, db_client, **kwargs)