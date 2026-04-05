from BaseClasses import Item, ItemClassification
import consts


class S3KItem(Item):
    game: str = consts.GAME

    def __init__(
            self,
            name: str,
            classification: ItemClassification,
            code: int = None,
            player: int = None,
    ):
        super(S3KItem, self).__init__(name, classification, code, player)
