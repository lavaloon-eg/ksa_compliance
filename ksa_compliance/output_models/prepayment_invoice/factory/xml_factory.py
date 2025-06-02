

from ..abs import Factory
from ..xml_tag import XMLAttribute, XMLTag


class XMLTagFactory(Factory):
    """
    Factory class to create XML tags for prepayment invoices.
    """

    @staticmethod
    def create(tag_name: str, attributes: dict = None, text: str = None) -> XMLTag:
        """
        Create an XMLTag instance with the given tag name, attributes, and text.
        
        :param tag_name: The name of the XML tag.
        :param attributes: A dictionary of attributes for the XML tag.
        :param text: The text content of the XML tag.
        :return: An instance of XMLTag.
        """
        if attributes is None:
            attributes = {}
        return XMLTag(tag_name, [XMLAttribute(name, value) for name, value in attributes.items()], text)
        