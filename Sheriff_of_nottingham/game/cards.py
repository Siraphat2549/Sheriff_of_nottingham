"""Card definitions for Sheriff of Nottingham."""
from dataclasses import dataclass
from enum import Enum


class CardType(Enum):
    APPLE = "Apple"
    CHEESE = "Cheese"
    BREAD = "Bread"
    CHICKEN = "Chicken"
    PEPPER = "Pepper"
    MEAD = "Mead"
    SILK = "Silk"
    CROSSBOW = "Crossbow"


LEGAL_GOODS = {CardType.APPLE, CardType.CHEESE, CardType.BREAD, CardType.CHICKEN}
CONTRABAND = {CardType.PEPPER, CardType.MEAD, CardType.SILK, CardType.CROSSBOW}

LEGAL_GOODS_LIST = [CardType.APPLE, CardType.CHEESE, CardType.BREAD, CardType.CHICKEN]


@dataclass
class CardInfo:
    card_type: CardType
    value: int       # gold earned when placed in stall
    penalty: int     # gold paid per card when caught
    count: int       # number of this card in the deck
    king_bonus: int = 0   # bonus for having most of this legal good
    queen_bonus: int = 0  # bonus for having second-most


# Official Sheriff of Nottingham card data
CARD_DATA = {
    CardType.APPLE:    CardInfo(CardType.APPLE,    2,  2, 10, 20, 10),
    CardType.CHEESE:   CardInfo(CardType.CHEESE,   3,  3, 10, 15, 10),
    CardType.BREAD:    CardInfo(CardType.BREAD,     3,  3, 10, 15, 10),
    CardType.CHICKEN:  CardInfo(CardType.CHICKEN,   4,  4, 10, 10,  5),
    CardType.PEPPER:   CardInfo(CardType.PEPPER,    9,  4,  6),
    CardType.MEAD:     CardInfo(CardType.MEAD,      7,  4,  6),
    CardType.SILK:     CardInfo(CardType.SILK,     11,  5,  6),
    CardType.CROSSBOW: CardInfo(CardType.CROSSBOW, 13,  6,  6),
}

CARD_EMOJI = {
    CardType.APPLE:    "Apple",
    CardType.CHEESE:   "Cheese",
    CardType.BREAD:    "Bread",
    CardType.CHICKEN:  "Chicken",
    CardType.PEPPER:   "Pepper",
    CardType.MEAD:     "Mead",
    CardType.SILK:     "Silk",
    CardType.CROSSBOW: "Crossbow",
}


class Card:
    """Represents a single game card."""

    def __init__(self, card_type: CardType):
        self.card_type = card_type
        self.info: CardInfo = CARD_DATA[card_type]

    @property
    def name(self) -> str:
        return self.card_type.value

    @property
    def is_legal(self) -> bool:
        return self.card_type in LEGAL_GOODS

    @property
    def is_contraband(self) -> bool:
        return self.card_type in CONTRABAND

    @property
    def value(self) -> int:
        return self.info.value

    @property
    def penalty(self) -> int:
        return self.info.penalty

    def __repr__(self) -> str:
        return f"Card({self.name})"

    def __eq__(self, other) -> bool:
        if isinstance(other, Card):
            return self.card_type == other.card_type
        return False

    def __hash__(self):
        return hash(self.card_type)
