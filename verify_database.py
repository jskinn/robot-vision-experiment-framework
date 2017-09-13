#!/bin/python
# Copyright (c) 2017, John Skinner
import sys
import os
import pykitti
import xxhash
import config.global_configuration as global_conf
import database.client
import database.entity_registry
import metadata.camera_intrinsics as cam_intr
import metadata.image_metadata as imeta


def check_collection(collection, db_client):
    all_entities = collection.find()
    failures = []
    for s_entity in all_entities:
        # patch the entity type if appropriate
        if not '.' in s_entity['_type']:
            qual_types = database.entity_registry.find_potential_entity_classes(s_entity['_type'])
            if len(qual_types) == 1 and qual_types[0] != s_entity['_type']:
                failures.append("Entity {0} had unqualified type {1}".format(s_entity['_id'], s_entity['_type']))
                #collection.update({'_id': s_entity['_id']}, {'$set': {'_type': qual_types[0]}})

        # Try and deserialize the entity, and validate it if we succeed
        entity = None
        try:
            entity = db_client.deserialize_entity(s_entity)
        except Exception as e:
            failures.append(str(e))
        if entity is not None and hasattr(entity, 'validate') and not entity.validate():
            failures.append("Entity {0} of type {1} failed to validate".format(s_entity['_id'], s_entity['_type']))

    for failure in failures:
        print(failure)


def patch_kitti_intrinsics(db_client, root_folder):
    for sequence_num in range(11):  # These are the only sequences with gt poses
        data = pykitti.odometry(root_folder, sequence="{0:02}".format(sequence_num))
        for left_image in data.cam2:
            camera_intrinsics = cam_intr.CameraIntrinsics(
                fx=data.calib.K_cam2[0, 0] / left_image.shape[1],
                fy=data.calib.K_cam2[1, 1] / left_image.shape[0],
                cx=data.calib.K_cam2[0, 2] / left_image.shape[1],
                cy=data.calib.K_cam2[1, 2] / left_image.shape[0])
            right_camera_intrinsics = cam_intr.CameraIntrinsics(
                fx=data.calib.K_cam3[0, 0] / left_image.shape[1],
                fy=data.calib.K_cam3[1, 1] / left_image.shape[0],
                cx=data.calib.K_cam3[0, 2] / left_image.shape[1],
                cy=data.calib.K_cam3[1, 2] / left_image.shape[0])
            image_ids = db_client.image_collection.find({
                'metadata.hash': xxhash.xxh64(left_image).digest(),
                'metadata.height': left_image.shape[0],
                'metadata.width': left_image.shape[1],
                'metadata.source_type': imeta.ImageSourceType.REAL_WORLD.value,
                'metadata.environment_type': imeta.EnvironmentType.OUTDOOR_URBAN.value,
                'metadata.light_level': imeta.LightingLevel.WELL_LIT.value,
                'metadata.time_of_day': imeta.TimeOfDay.AFTERNOON.value
            }, {'_id': True})
            for s_image in image_ids:
                db_client.image_collection.update({'_id': s_image['_id']}, {
                    '$set': {
                        'additional_metadata.dataset': 'KITTI',
                        'additional_metadata.sequence': sequence_num,
                        'metadata.intrinsics': camera_intrinsics.serialize(),
                        'metadata.right_intrinsics': right_camera_intrinsics.serialize()
                    }
                })


def main(*args):
    """
    Run a given system with a given image source.
    This represents a basic task.
    Scripts to run this will be autogenerated by the job system
    The first argument is the system id, the second argument is the image source to use
    (note that args[0] should be the x
    :return:
    """
    config = global_conf.load_global_config('config.yml')
    db_client = database.client.DatabaseClient(config=config)

    patch_kitti_intrinsics(db_client, os.path.expanduser(os.path.join('~', 'datasets', 'KITTI', 'dataset')))

    # Make sure we got all the kitti images
    kitti_datasets = db_client.experiments_collection.find_one({
        '_type': 'experiments.visual_slam.visual_slam_experiment.VisualSlamExperiment'
    }, {'kitti_datasets': True})['kitti_datasets']
    for image_source_id in kitti_datasets:
        s_image_source = db_client.image_source_collection.find_one({'_id': image_source_id}, {'images': True})
        for _, image_id in s_image_source['images']:
            s_image = db_client.image_collection.find_one({'_id': image_id},
                                                          {'additional_metadata': True, 'metadata': True})
            assert 'dataset' in s_image['additional_metadata']
            assert 'sequence' in s_image['additional_metadata']
            assert s_image['metadata']['intrinsics']['cx'] > 0
            assert s_image['metadata']['intrinsics']['cy'] > 0

    # Find the libviso2 systems and ORBSLAM2 systems
    system_ids = {s_system['_id'] for s_system in db_client.system_collection.find({
        '_type': {'$in': ['systems.visual_odometry.libviso2.libviso2.LibVisOSystem', 'systems.slam.orbslam2.ORBSLAM2']}
    }, {'_id': True})}
    # Find all trials for those system ids
    trials_to_remove = set()
    for system_id in system_ids:
        trials_to_remove |= {s_trial['_id'] for s_trial in db_client.trials_collection.find({
            'system': system_id
        }, {'_id': True})}
    db_client.trials_collection.remove({
        '_id': {'$in': list(trials_to_remove)}
    })
    # Remove benchmark results for bad trials
    results_to_remove = {s_result['_id'] for s_result in db_client.results_collection.find({
        'trial_result': {'$in': list(trials_to_remove)}
    })}
    db_client.results_collection.remove({
        '_id': {'$in': list(results_to_remove)}
    })
    # Remove tasks with invalid results
    db_client.tasks_collection.remove({
        'result': {'$in': list(trials_to_remove | results_to_remove)}
    })

    # Patch saved entity types to fully-qualified names
    #check_collection(db_client.trainer_collection, db_client)
    #check_collection(db_client.trainee_collection, db_client)
    #check_collection(db_client.system_collection, db_client)
    #check_collection(db_client.image_source_collection, db_client)
    #check_collection(db_client.image_collection, db_client)
    #check_collection(db_client.trials_collection, db_client)
    #check_collection(db_client.benchmarks_collection, db_client)
    #check_collection(db_client.results_collection, db_client)
    #check_collection(db_client.experiments_collection, db_client)


if __name__ == '__main__':
    main(*sys.argv[1:])
