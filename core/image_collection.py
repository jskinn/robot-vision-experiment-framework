import abc
import database.entity
import core.image
import core.sequence_type
import core.image_source


class ImageCollection(core.image_source.ImageSource, database.entity.Entity, metaclass=abc.ABCMeta):
    """
    A collection of images stored in the database.
    This can be a sequential set of images like a video, or a random sampling of different pictures.
    """

    def __init__(self, images, type, id_=None, **kwargs):
        super().__init__(id=id_, **kwargs)

        self._images = images
        if isinstance(type, core.sequence_type.ImageSequenceType):
            self._sequence_type = type
        else:
            self._sequence_type = core.sequence_type.ImageSequenceType.NON_SEQUENTIAL
        self._is_depth_available = all(hasattr(image, 'depth_filename') and
                                       image.depth_filename is not None for image in images)
        self._is_labels_available = all(hasattr(image, 'labels_filename') and
                                        image.labels_filename is not None for image in images)
        self._is_normals_available = all(hasattr(image, 'labels_filename') and
                                         image.world_normals_filename is not None for image in images)
        self._is_stereo_available = all(hasattr(image, 'left_filename') and
                                        hasattr(image, 'right_filename') for image in images)
        self._current_index = 0

    def __len__(self):
        return len(self._images)

    def __iter__(self):
        return iter(self._images)

    @property
    def sequence_type(self):
        """
        Get the type of image sequence produced by this image source.
        This is determined when creating the image collection
        It is useful for determining which sources can run with which algorithms.
        :return: The image sequence type enum
        :rtype core.image_sequence.ImageSequenceType:
        """
        return self._sequence_type

    def begin(self):
        """
        Start producing images.
        Resets the current index to the start
        :return: True
        """
        self._current_index = 0
        return True

    def get_next_image(self):
        """
        Blocking get the next image from this source.
        Parallel versions of this may add a timeout parameter.
        Returning None indicates that this image source will produce no more images

        :return: An Image object (see core.image) or None
        """
        if not self.is_complete():
            result = self._images[self._current_index]
            self._current_index += 1
            return result
        return None

    def is_complete(self):
        """
        Have we got all the images from this source?
        Some sources are infinite, some are not,
        and this method lets those that are not end the iteration.
        :return: True if there are more images to get, false otherwise.
        """
        return self._current_index >= len(self)

    @property
    def is_depth_available(self):
        """
        Do the images in this sequence include depth
        :return: True if depth is available for all images in this sequence
        """
        return self._is_depth_available

    @property
    def is_labels_available(self):
        """
        Do images from this image source include object lables
        :return: True if this image source can produce object labels for each image
        """
        return self._is_labels_available

    @property
    def is_normals_available(self):
        """
        Do images from this image source include world normals
        :return: True if images have world normals associated with them 
        """
        return self._is_normals_available

    @property
    def is_stereo_available(self):
        """
        Can this image source produce stereo images.
        Some algorithms only run with stereo images
        :return:
        """
        return self._is_stereo_available

    def validate(self):
        """
        The image sequence is valid iff all the contained images are valid
        Only count the images that have a validate method
        :return: True if all the images are valid, false if not
        """
        for image in self._images:
            if hasattr(image, 'validate'):
                if not image.validate():
                    return False
        return True

    def serialize(self):
        serialized = super().serialize()
        # Only include the image IDs here, they'll get turned back into objects for us
        serialized['images'] = [image.identifier for image in self._images]
        if self.sequence_type is core.sequence_type.ImageSequenceType.SEQUENTIAL:
            serialized['sequence_type'] = 'SEQ'
        else:
            serialized['sequence_type'] = 'NON'
        return serialized

    @classmethod
    def deserialize(cls, serialized_representation, **kwargs):
        # Note: These images should already be deserialized
        if 'images' in serialized_representation:
            kwargs['images'] = serialized_representation['images']
        if 'sequence_type' in serialized_representation and serialized_representation['sequence_type'] is 'SEQ':
            kwargs['type'] = core.sequence_type.ImageSequenceType.SEQUENTIAL
        else:
            kwargs['type'] = core.sequence_type.ImageSequenceType.NON_SEQUENTIAL
        return super().deserialize(serialized_representation, **kwargs)


def load_image_collection(dbclient, id_):
    """
    Load any collection of images.
    This handles the weird chicken-and-egg problem of deserializing
    the image collection and the individual images.

    :param dbclient: An instance of database.client, from which to load the image collection 
    :param id_: The ID of the image collection
    :return: A deserialized 
    """

    # step 1: Get the serialized dataset
    s_collection = dbclient.datasets.find_one({'_id': id_})

    # step 2: load the images from the serialized ids
    image_ids = s_collection['images']
    s_images = dbclient.images.find({'_id': {'$in': image_ids}})
    images = [dbclient.deserialize_entity(s_image) for s_image in s_images]

    # step 3: replace the image ids with their deserialized versions
    s_collection['images'] = images

    # step 4: deserialize and return the dataset
    return dbclient.deserialize_entity(s_collection)