import pickle
import bson
import core.trial_result
import util.transform as tf
import trials.slam.tracking_state as track_state


class SLAMTrialResult(core.trial_result.TrialResult):
    """
    The results of running a Monocular SLAM system.
    Has the ground truth and computed trajectories,
    and the tracking statistics.
    """
    def __init__(self, image_source_id, system_id, trajectory, ground_truth_trajectory, tracking_stats,
                 system_settings, id_=None, **kwargs):
        kwargs['success'] = True
        super().__init__(image_source_id=image_source_id, system_id=system_id,
                         system_settings=system_settings, id_=id_, **kwargs)
        self._trajectory = trajectory
        self._ground_truth_trajectory = ground_truth_trajectory
        self._tracking_stats = tracking_stats

    @property
    def trajectory(self):
        return self._trajectory

    @property
    def tracking_stats(self):
        return self._tracking_stats

    @property
    def ground_truth_trajectory(self):
        return self._ground_truth_trajectory

    def get_ground_truth_camera_poses(self):
        return self.ground_truth_trajectory

    def get_computed_camera_poses(self):
        return self.trajectory

    def get_tracking_states(self):
        return self.tracking_stats

    def serialize(self):
        serialized = super().serialize()
        #serialized['ground_truth_trajectory'] = {timestamp: tf.serialize_transform(pose)
        #                                         for timestamp, pose in self.ground_truth_trajectory.items()}
        #serialized['trajectory'] = {timestamp: tf.serialize_transform(pose)
        #                            for timestamp, pose in self.trajectory.items()}
        #serialized['tracking_stats'] = {timestamp: str(tracking_state)
        #                                for timestamp, tracking_state in self.tracking_stats.items()}
        serialized['ground_truth_trajectory'] = bson.Binary(pickle.dumps(self.ground_truth_trajectory, protocol=pickle.HIGHEST_PROTOCOL))
        serialized['trajectory'] = bson.Binary(pickle.dumps(self.trajectory, protocol=pickle.HIGHEST_PROTOCOL))
        serialized['tracking_stats'] = bson.Binary(pickle.dumps(self.tracking_stats, protocol=pickle.HIGHEST_PROTOCOL))
        return serialized

    @classmethod
    def deserialize(cls, serialized_representation, **kwargs):
        if 'ground_truth_trajectory' in serialized_representation:
            kwargs['ground_truth_trajectory'] = pickle.loads(serialized_representation['ground_truth_trajectory'])
        if 'trajectory' in serialized_representation:
            kwargs['trajectory'] = pickle.loads(serialized_representation['trajectory'])
        if 'tracking_stats' in serialized_representation:
            kwargs['tracking_stats'] = pickle.loads(serialized_representation['tracking_stats'])
        return super().deserialize(serialized_representation, **kwargs)
