# Copyright (c) 2017, John Skinner
import abc
import database.entity


class VisionSystem(database.entity.Entity, metaclass=database.entity.AbstractEntityMetaclass):
    """
    A Vision system, something that will be run, benchmarked, and analysed by this program.
    This is the standard interface that everything must implement to work with this system.
    All systems must be entities and stored in the database, so that the framework can load them, and 
    """

    @property
    @abc.abstractmethod
    def is_deterministic(self):
        """
        Is the visual system deterministic.

        If this is false, it will have to be tested multiple times, because the performance will be inconsistent
        between runs.

        :return: True iff the algorithm will produce the same results each time.
        :rtype: bool
        """
        pass

    @abc.abstractmethod
    def is_image_source_appropriate(self, image_source):
        """
        Is the dataset appropriate for testing this vision system.
        :param image_source: The source for images that this system will potentially be run with.
        :return: True iff the particular dataset is appropriate for this vision system.
        :rtype: bool
        """
        pass

    @abc.abstractmethod
    def set_camera_intrinsics(self, camera_intrinsics):
        """
        Set the intrinsics used by this image source to process images.
        Many systems take this as configuration.
        :param camera_intrinsics: A camera intrinsics object.
        :return:
        """
        pass

    def set_stereo_baseline(self, baseline):
        """
        Set the stereo baseline for stereo systems.
        Other systems don't need to override this, it will do nothing.
        :param baseline: The distance between the stereo cameras, as a float
        :return:
        """
        pass

    @abc.abstractmethod
    def start_trial(self, sequence_type):
        """
        Start a trial with this system.
        After calling this, we can feed images to the system.
        When the trial is complete, call finish_trial to get the result.
        :param sequence_type: Are the provided images part of a sequence, or just unassociated pictures.
        :return: void
        """
        pass

    @abc.abstractmethod
    def process_image(self, image, timestamp):
        """
        Process an image as part of the current run.
        Should automatically start a new trial if none is currently started.
        :param image: The image object for this frame
        :param timestamp: A timestamp or index associated with this image. Sometimes None.
        :return: void
        """
        pass

    @abc.abstractmethod
    def finish_trial(self):
        """
        End the current trial, returning a trial result.
        Return none if no trial is started.
        :return:
        :rtype TrialResult:
        """
        return None
