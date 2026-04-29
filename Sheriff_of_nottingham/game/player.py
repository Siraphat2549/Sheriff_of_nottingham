"""Player class for Sheriff of Nottingham."""
from typing import List, Dict, Optional
from collections import Counter
from game.cards import Card, CardType, LEGAL_GOODS, CARD_DATA


class MerchantBag:
    """Represents a player's merchant bag for a round."""

    def __init__(self):
        self.cards: List[Card] = []
        self.declared_type: Optional[CardType] = None
        self.declared_quantity: int = 0
        self.bribe_offered: int = 0

    def is_honest(self) -> bool:
        """Check if the bag contents match the declaration."""
        if not self.declared_type:
            return False
        if len(self.cards) != self.declared_quantity:
            return False
        return all(c.card_type == self.declared_type for c in self.cards)

    def clear(self):
        self.cards.clear()
        self.declared_type = None
        self.declared_quantity = 0
        self.bribe_offered = 0

    @property
    def is_ready(self) -> bool:
        return len(self.cards) > 0 and self.declared_type is not None and self.declared_quantity > 0


class Player:
    """Represents a game participant (human or AI)."""

    STARTING_GOLD = 50

    def __init__(self, name: str, is_ai: bool = False, ai_difficulty: str = "medium"):
        self.name = name
        self.is_ai = is_ai
        self.ai_difficulty = ai_difficulty  # 'easy', 'medium', 'hard'

        self.gold: int = self.STARTING_GOLD
        self.hand: List[Card] = []
        self.stall: List[Card] = []  # goods successfully brought into city
        self.bag: MerchantBag = MerchantBag()

        # Statistics
        self.times_caught: int = 0
        self.times_inspected: int = 0
        self.successful_smuggles: int = 0
        self.rounds_as_sheriff: int = 0

    def add_to_hand(self, cards: List[Card]):
        """Add cards to this player's hand."""
        self.hand.extend(cards)

    def remove_from_hand(self, card: Card) -> bool:
        """Remove a specific card from hand. Returns True if removed."""
        for i, c in enumerate(self.hand):
            if c.card_type == card.card_type:
                self.hand.pop(i)
                return True
        return False

    def remove_many_from_hand(self, cards: List[Card]) -> List[Card]:
        """Remove multiple cards from hand, return successfully removed."""
        removed = []
        hand_copy = self.hand[:]
        for card in cards:
            for i, c in enumerate(hand_copy):
                if c.card_type == card.card_type:
                    removed.append(hand_copy.pop(i))
                    break
        self.hand = hand_copy
        return removed

    def pack_bag(self, cards: List[Card], declared_type: CardType, declared_quantity: int):
        """Pack the merchant bag with selected cards and a declaration."""
        self.bag.clear()
        self.bag.cards = cards[:]
        self.bag.declared_type = declared_type
        self.bag.declared_quantity = declared_quantity

    def accept_bag_into_stall(self):
        """Move bag contents to stall (goods passed inspection)."""
        self.stall.extend(self.bag.cards)
        self.bag.clear()

    def discard_bag(self) -> List[Card]:
        """Return bag cards (to be discarded), clear bag."""
        cards = self.bag.cards[:]
        self.bag.clear()
        return cards

    def earn_gold(self, amount: int):
        """Add gold to player's treasury."""
        self.gold += amount

    def pay_gold(self, amount: int) -> int:
        """Pay gold; player can't go below 0. Returns actual amount paid."""
        paid = min(self.gold, amount)
        self.gold -= paid
        return paid

    @property
    def stall_value(self) -> int:
        """Total value of goods in stall."""
        return sum(c.value for c in self.stall)

    @property
    def stall_counts(self) -> Counter:
        """Count of each card type in stall."""
        return Counter(c.card_type for c in self.stall)

    @property
    def hand_counts(self) -> Counter:
        """Count of each card type in hand."""
        return Counter(c.card_type for c in self.hand)

    @property
    def hand_size(self) -> int:
        return len(self.hand)

    def final_score(self, king_bonuses: Dict[CardType, int], queen_bonuses: Dict[CardType, int]) -> int:
        """Calculate final score including stall value, gold, and bonuses."""
        score = self.gold + self.stall_value
        counts = self.stall_counts
        for card_type, count in counts.items():
            info = CARD_DATA[card_type]
            if card_type in LEGAL_GOODS:
                bonus = king_bonuses.get(card_type, 0) if king_bonuses.get("_winner_" + card_type.value) == self.name else 0
                queen_bonus = queen_bonuses.get(card_type, 0) if queen_bonuses.get("_second_" + card_type.value) == self.name else 0
                score += bonus + queen_bonus
        return score

    def __repr__(self) -> str:
        return f"Player({self.name}, gold={self.gold}, hand={len(self.hand)})"
