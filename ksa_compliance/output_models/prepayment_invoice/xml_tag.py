
class XMLAttribute:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return f'{self.name}="{self.value}"'

class XMLTag:
    def __init__(self, tag_name, attributes=None, text=None):
        self.tag_name = tag_name
        self.attributes = attributes
        self.text = text