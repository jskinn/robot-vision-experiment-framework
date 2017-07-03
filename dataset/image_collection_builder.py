import copy
import core.image_collection
import core.image_entity
import core.sequence_type
import util.database_helpers as db_help


class ImageCollectionBuilder:
    """
    A builder to create image collections within the database
    """

    def __init__(self, db_client):
        self._db_client = db_client
        self._image_ids = []
        self._sequence_type = core.sequence_type.ImageSequenceType.SEQUENTIAL

    def set_non_sequential(self):
        """
        Change the sequence type of the built sequence to non-sequential.
        The default is sequential
        :return: void
        """
        self._sequence_type = core.sequence_type.ImageSequenceType.NON_SEQUENTIAL

    def add_image(self, image):
        """
        Add an image to the growing image collection.
        Does not affect the sequence type, you may need to set that manually.
        :param image: An image_entity or image object.
        :return: void
        """
        if hasattr(image, 'identifier') and image.identifier is not None:
            # Image is already in the database, just store it's id
            self._image_ids.append(image.identifier)
        else:
            image_id = core.image_entity.save_image(self._db_client, image)
            if image_id is not None:
                self._image_ids.append(image_id)

    def add_from_image_source(self, image_source, filter_function=None):
        """
        Read an image source, and save it in the database as an image collection.
        This is used to both save datasets from simulation,
        and to sample existing datasets into new collections.

        :param image_source: The image source to save
        :param filter_function: A function used to filter the images that will be part of the new collection.
        :return:
        """
        if (len(self._image_ids) > 0 or
                image_source.sequence_type == core.sequence_type.ImageSequenceType.NON_SEQUENTIAL):
            self._sequence_type = core.sequence_type.ImageSequenceType.NON_SEQUENTIAL
        image_source.begin()
        while not image_source.is_complete():
            image, _ = image_source.get_next_image()
            if not callable(filter_function) or filter_function(image):
                self.add_image(image)

    def save(self):
        """
        Store the image collection in the database.
        Checks if such an image collection already exists.
        :return: The id of the image collection in the database
        """
        if len(self._image_ids) > 0:
            s_collection = core.image_collection.ImageCollection.create_serialized(
                image_ids=self._image_ids,
                sequence_type=self._sequence_type
            )
            query = db_help.query_to_dot_notation(copy.deepcopy(s_collection))
            existing = self._db_client.image_source_collection.find_one(query, {'_id': True})
            if existing is not None:
                return existing['_id']
            else:
                return self._db_client.image_source_collection.insert(s_collection)
        return None
